import asyncio
from threading import Thread
from xmlrpc.client import ServerProxy
from typing import Any, List
from enum import Enum
from Address import Address
import socket
import time
from msgs.ApplyMembershipMsg import ApplyMembershipReq, ApplyMembershipResp
from msgs.BaseMsg import BaseMsg
from msgs.HeartbeatMsg import HeartbeatResp
from msgs.ExecuteMsg import ExecuteReq, ExecuteResp
from utils.MsgParser import MsgParser
from structs.Log import Log
from msgs.VoteMsg import VoteReq, VoteResp

class RaftNode:
    # FIXME: knp di dalem class? mending taro luar biar bisa dipake
    HEARTBEAT_INTERVAL = 1
    ELECTION_TIMEOUT_MIN = 2
    ELECTION_TIMEOUT_MAX = 3
    RPC_TIMEOUT = 0.5

    class NodeType(Enum):
        LEADER = 1
        CANDIDATE = 2
        FOLLOWER = 3

    class FuncRPC(Enum):
        APPLY_MEMBERSHIP = "apply_membership"
        VOTE_LEADER = "vote_leader"

    # Heeh, semua yang diatas dari komen ini

    def __init__(self, application: Any, addr: Address, contact_addr: Address = None):
        socket.setdefaulttimeout(RaftNode.RPC_TIMEOUT)
        self.address:             Address = addr
        self.app:                 Any = application

        # stable storage vars
        self.__try_fetch_stable()

        # volatile vars
        self.__init_volatile()

        # additional vars
        self.cluster_addr_list:   List[Address] = [] # FIXME: Lebih baik dijadiin struct ajah, daripada bergantung dengan index, karena di join sama data last sent
        self.msg_parser: MsgParser = MsgParser()

        if contact_addr is None:
            self.cluster_addr_list.append(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)

    def __on_recover_crash(self):
        self.__try_fetch_stable()
        self.__init_volatile()

    def __try_fetch_stable(self):
        # TODO: get stable storage
        # if exist persistence, get persistence, return

        self.__init_stable()

    def __init_stable(self):
        self.election_term:       int = 0
        self.voted_for: Address     = None # TODO: add type, #QUESTIONABLE: hah ngapain dia voted ke selain candidate?
        self.log:                 List[Log] = []
        self.commit_length: int = 0

    def __init_volatile(self):
        self.type:                RaftNode.NodeType = RaftNode.NodeType.FOLLOWER
        self.cluster_leader_addr: Address = None
        self.votes_received: List[Address] = [] # FIXME: Ini mah gausah disimpen, sementara
        self.sent_length = [] # FIXME: Sent length gaperlu, ini bukan tcp wkwk
        self.acked_length = []

    def vote_leader(self):
        self.election_term += 1
        self.type = RaftNode.NodeType.CANDIDATE
        self.voted_for = self.address # FIXME: voted_for = leader_addr? ato beda? bisa disamain kok
        self.votes_received = [self.address]
        
        last_term = 0
        if len(self.log) > 0:
            last_term = self.log[-1]["term"]

        # FIXME: Check konsistensi log juga
        
        msg = VoteReq({
            'voted_for': self.voted_for, 
            'term': self.election_term,
            'log_length': len(self.log),
            'last_term': last_term, # FIXME: Last term buat apa?
        })

        for i in range(len(self.cluster_addr_list)):
            addr = self.cluster_addr_list[i]
            self.__try_request_vote(
                addr, msg
            )
            # TODO: start timer
        # TODO: pindahin start timer ke sini

    def __try_request_vote(self, addr_dest: Address, msg: VoteReq):
        redirected_addr = addr_dest
        response = VoteResp({
            'status': "redirected",
            "address": addr_dest,
        })

        while response["status"] != "success": # FIXME: Recursive redirected gini seharusnya di bikin wrapper aja biar bisa dipake lagi
            redirected_addr = Address(
                response["address"]["ip"],
                response["address"]["port"],
            )
            print(f"sending msg: {msg}")
            response: VoteResp = self.__send_request(
                msg,
                RaftNode.FuncRPC.VOTE_LEADER.value,
                redirected_addr
            )
        
        # TODO: handle response

    # Internal Raft Node methods

    def __print_log(self, text: str): # FIXME: Plis jangan print_log gua kira ngeprint isi log
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address # FIXME: cluster_leader_addr = voted_for? ato beda? bisa disamain kok
        self.type = RaftNode.NodeType.LEADER
        request = {
            "cluster_leader_addr": self.address
        }
        # TODO : Inform to all node this is new leader
        self.heartbeat_thread = Thread(target=asyncio.run, args=[ #FIXME: berarti klo bukan leader, thread loopnya beda lagi?
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    async def __leader_heartbeat(self):
        # TODO : Send periodic heartbeat
        while True:
            self.__print_log("[Leader] Sending heartbeat...")
            pass # FIXME: WHaat?
            await asyncio.sleep(RaftNode.HEARTBEAT_INTERVAL)

    def __try_to_apply_membership(self, contact_addr: Address):
        redirected_addr = contact_addr
        response = ApplyMembershipResp({
            "status": "redirected",
            "address": contact_addr
        })
        while response["status"] != "success":
            redirected_addr = Address(
                response["address"]["ip"], response["address"]["port"])
            msg = ApplyMembershipReq(self.address)
            print(f"Sending msg : {msg}")
            response: ApplyMembershipResp = self.__send_request(
                msg, RaftNode.FuncRPC.APPLY_MEMBERSHIP.value, redirected_addr)
        self.log = response["log"]
        self.cluster_addr_list = response["cluster_addr_list"]
        self.cluster_leader_addr = redirected_addr

    def __send_request(self, request: BaseMsg, rpc_name: str, addr: Address) -> BaseMsg:
        # Warning : This method is blocking
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = self.msg_parser.serialize(request)
        print(f"Sending request to {addr.ip}:{addr.port}...")
        print(f"rpc_name : {rpc_name}")
        rpc_function = getattr(node, rpc_name)
        print(f"RPC function : {rpc_function}")
        response = self.msg_parser.deserialize(rpc_function(json_request))
        self.__print_log(response)
        return response

    # Inter-node RPCs
    def heartbeat(self, json_request: str) -> str:
        # TODO : Implement heartbeat, reappend log baru dan check commitnya juga
        response = HeartbeatResp({
            "heartbeat_response": "ack",
            "address":            self.address,
        })
        return self.msg_parser.serialize(response)

    # Client RPCs
    def apply_membership(self, json_request: str) -> str: #FIXME: apply membership pake consensus, dan blocking 1 persatu
        # TODO : Implement apply_membership
        request = self.msg_parser.deserialize(json_request)
        print(f"Request : {request}")
        self.cluster_addr_list.append(Address(request["ip"], request["port"]))
        response = ApplyMembershipResp({
            "status":            "success",
            "log":               self.log, # FIXME: log terbaru apa semua? yang terbaru aja
            "cluster_addr_list": self.cluster_addr_list,
        })
        return self.msg_parser.serialize(response)

    def execute(self, json_request: str) -> str:
        request: ExecuteReq = self.msg_parser.deserialize(json_request)
        # TODO : Implement execute
        response = ExecuteResp({})
        return self.msg_parser.serialize(response)
