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
from msgs.HeartbeatMsg import HeartbeatResp, HeartbeatRespType, HeartbeatReq
from msgs.ExecuteMsg import ExecuteReq, ExecuteResp
from utils.MsgParser import MsgParser
from structs.Log import Log
from msgs.VoteMsg import VoteReq, VoteResp
from msgs.BaseMsg import BaseReq, BaseResp, RespStatus
from typing import TypedDict, TypeVar, Generic
from msgs.ErrorMsg import ErrorResp
import json

T = TypeVar('T', bound=TypedDict)

class StableStorage(Generic[T]):
    def __init__(self, addr: Address):
        self.id = self.__id_from_addr(addr)
        self.path = f"persistence/{self.id}.json"

    def __id_from_addr(self, addr: Address):
        return f"{addr.ip}_{addr.port}"

    def __store(self, data: str):
        with open(self.path, 'w') as f:
            f.write(data)
    
    def __load(self):
        with open(self.path, 'r') as f:
            return f.read()
    
    def load(self) -> T:
        return json.loads(self.__load())
    
    def update(self, key: str, value: Any) -> T:
        data = self.load()
        data[key] = value
        str_data = json.dumps(data)
        self.__store(str_data)

        return data
    
    def storeAll(self, data: T) -> T:
        str_data = json.dumps(data)
        self.__store(str_data)

        return data
    
    def try_load(self):
        try:
            return self.load()
        except:
            return None

class RPCHandler:
    def __init__(self):
        self.msg_parser = MsgParser()

    def __call(self, addr: Address, rpc_name: str, msg: BaseMsg):
        node = ServerProxy(f"http://{addr.ip}:{addr.port}")
        json_request = self.msg_parser.serialize(msg)
        print(f"Sending request to {addr.ip}:{addr.port}...")
        rpc_function = getattr(node, rpc_name)

        try:
            response = rpc_function(json_request)
            print(f"Response from {addr.ip}:{addr.port}: {response}")
            return response
        except Exception as e:
            print(f"Error while sending request to {addr.ip}:{addr.port}: {e}")
            return json.dumps(ErrorResp({
                'status': RespStatus.FAILED.value,
                'address': addr,
                'error': str(e),
            }))
    
    def request(self, addr: Address, rpc_name: str, msg: BaseMsg):
        redirect_addr = addr
        response = BaseResp({
            'status': RespStatus.REDIRECTED.value,
            'address': redirect_addr,
        })

        while response["status"] == RespStatus.REDIRECTED.value:
            redirect_addr = Address(
                response["address"]["ip"],
                response["address"]["port"],
            )
            response = self.msg_parser.deserialize(self.__call(redirect_addr, rpc_name, msg))
        
        # TODO: handle fail response
        if response["status"] == RespStatus.FAILED.value:
            print("Failed to send request")
            # exit(1)
            raise Exception(response["error"])

        response["address"] = redirect_addr
        return response

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
        REQUEST_VOTE = "request_vote"
        HEARTBEAT = "heartbeat"
    
    class StableVars(TypedDict):
        election_term: int
        voted_for: Address     
        log: List[Log] 
        commit_length: int


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
        self.rpc_handler: RPCHandler = RPCHandler()

        if contact_addr is None:
            self.cluster_addr_list.append(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)
        
        self.__init_heartbeat()

    def __on_recover_crash(self):
        self.__try_fetch_stable()
        self.__init_volatile()

    def __try_fetch_stable(self):
        self.stable_storage = StableStorage[RaftNode.StableVars](self.address)
        loaded = self.stable_storage.try_load()
        if loaded is not None:
            self.__print_log(f"Loaded stable storage: {loaded}")
            return

        self.__init_stable()

    def __init_stable(self):
        data = RaftNode.StableVars({
            'election_term': 0,
            'voted_for': None,
            'log': [],
            'commit_length': 0,
        })
        self.stable_storage.storeAll(data)

    def __init_volatile(self):
        self.type:                RaftNode.NodeType = RaftNode.NodeType.FOLLOWER
        self.cluster_leader_addr: Address = None
        self.votes_received: List[Address] = [] # FIXME: Ini mah gausah disimpen, sementara
        self.sent_length = [] # FIXME: Sent length gaperlu, ini bukan tcp wkwk
        self.acked_length = []

    def vote_leader(self):
        stable_vars = self.stable_storage.load()

        stable_vars = self.stable_storage.update('election_term', stable_vars['election_term'] + 1)
        stable_vars = self.stable_storage.update('voted_for', self.address) # FIXME: voted_for = leader_addr? ato beda? bisa disamain kok
        self.type = RaftNode.NodeType.CANDIDATE
        self.votes_received = [self.address]
        
        last_term = 0
        if len(stable_vars["log"]) > 0:
            last_term = stable_vars["log"][-1]["term"]

        # FIXME: Check konsistensi log juga
        
        msg = VoteReq({
            'voted_for': stable_vars["voted_for"], 
            'term': stable_vars["election_term"],
            'log_length': len(stable_vars["log"]),
            'last_term': last_term, # FIXME: Last term buat apa?
        })

        for i in range(len(self.cluster_addr_list)):
            addr = self.cluster_addr_list[i]
            # TODO: make sure async
            asyncio.create_task(self.__try_request_vote(addr, msg))

        # TODO: start timer
        # TODO: pindahin start timer ke sini

    async def __try_request_vote(self, addr_dest: Address, msg: VoteReq):
        response = self.rpc_handler.request(
            addr_dest,
            RaftNode.FuncRPC.REQUEST_VOTE.value,
            msg,
        )

        voter_id = response["node_addr"]
        voter_term = response["current_term"]
        granted = response["granted"]

        stable_vars = self.stable_storage.load()
        # election_term = stable_vars["election_term"]

        if self.type == RaftNode.NodeType.CANDIDATE and stable_vars["election_term"] == voter_term and granted:
            self.votes_received.append(voter_id)
            if len(self.votes_received) >= (len(self.cluster_addr_list) + 1) / 2:
                self.__initialize_as_leader()
                # TODO: cancel election timer
                # TODO: replicate log for all cluster nodes
        elif voter_term > stable_vars["election_term"]:
            stable_vars["election_term"] = voter_term
            stable_vars["voted_for"] = None
            self.stable_storage.storeAll(stable_vars)

            self.type = RaftNode.NodeType.FOLLOWER
            # TODO: cancel election timer
        
    
    def request_vote(self, json_request: str):
        request: VoteReq = self.msg_parser.deserialize(json_request)
        print(f"request vote: {request}")

        cId = request["voted_for"]
        cTerm = request["term"]
        cLogLength = request["log_length"]
        cLogTerm = request["last_term"]

        stable_vars = self.stable_storage.load()
        
        if cTerm > stable_vars["election_term"]:
            stable_vars["election_term"] = cTerm
            stable_vars["voted_for"] = None
            self.stable_storage.storeAll(stable_vars)

            self.type = RaftNode.NodeType.FOLLOWER
        
        last_term = 0
        if len(stable_vars["log"]) > 0:
            last_term = stable_vars["log"][-1]["term"]
        
        logOk = (cLogTerm > last_term) or (cLogTerm == last_term and cLogLength >= len(stable_vars["log"]))

        response = VoteResp({
            'status': "success",
            'address': self.address,
            'node_addr': self.address,
            'current_term': stable_vars["election_term"],            
        })

        if (cTerm == stable_vars["election_term"] and logOk 
            and (stable_vars["voted_for"] is None or stable_vars["voted_for"] == cId)):
            self.stable_storage.update('voted_for', cId)
            response["vote_granted"] = True
        else:
            response["vote_granted"] = False
        
        print(f"response vote: {response}")
        return self.msg_parser.serialize(response)
        
    # Internal Raft Node methods

    def __print_log(self, text: str): # FIXME: Plis jangan print_log gua kira ngeprint isi log
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __init_heartbeat(self):
        # TODO : Inform to all node this is new leader
        self.heartbeat_thread = Thread(target=asyncio.run, args=[ #FIXME: berarti klo bukan leader, thread loopnya beda lagi?
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address # FIXME: cluster_leader_addr = voted_for? ato beda? bisa disamain kok
        self.type = RaftNode.NodeType.LEADER
        # request = {
        #     "cluster_leader_addr": self.address
        # }
        # # TODO : Inform to all node this is new leader
        # self.heartbeat_thread = Thread(target=asyncio.run, args=[ #FIXME: berarti klo bukan leader, thread loopnya beda lagi?
        #                                self.__leader_heartbeat()])
        # self.heartbeat_thread.start()

    async def __leader_heartbeat(self):
        # TODO : Send periodic heartbeat
        while True:
            if self.type == RaftNode.NodeType.LEADER:
                self.__print_log("[Leader] Sending heartbeat...")
                pass # FIXME: WHaat?

                # TODO : Send heartbeat to all node
                for i in range(len(self.cluster_addr_list)):
                    if self.cluster_addr_list[i] == self.address:
                        continue

                    addr = self.cluster_addr_list[i]
                    stable_vars = self.stable_storage.load()

                    # TODO: calc prefix len
                    prefix_len = 0
                    suffix = stable_vars["log"][prefix_len:]
                    prefix_term = 0
                    if prefix_len > 0:
                        prefix_term = stable_vars["log"][prefix_len - 1]["term"]

                    msg = HeartbeatReq({
                        "leader_addr": self.address,
                        "term": stable_vars["election_term"],
                        "prefix_len": prefix_len,
                        "prefix_term": prefix_term,
                        "suffix": suffix,
                        "commit_length": stable_vars["commit_length"],
                    })
                    
                    self.rpc_handler.request(
                        addr,
                        RaftNode.FuncRPC.HEARTBEAT.value,
                        msg,
                    )

            await asyncio.sleep(RaftNode.HEARTBEAT_INTERVAL)

    def __try_to_apply_membership(self, contact_addr: Address):
        msg = ApplyMembershipReq(self.address)
        print(f"Sending msg : {msg}")
        response: ApplyMembershipResp = self.rpc_handler.request(
            contact_addr, RaftNode.FuncRPC.APPLY_MEMBERSHIP.value, msg)
        
        # TODO: handle failed response
        self.__print_log(f"Response : {response}")
        self.stable_storage.update("log", response["log"])
        self.cluster_addr_list = response["cluster_addr_list"]
        self.cluster_leader_addr = response["address"]

    # Inter-node RPCs
    def heartbeat(self, json_request: str) -> str:
        # TODO : Implement heartbeat, reappend log baru dan check commitnya juga
        request = self.msg_parser.deserialize(json_request)
        self.__print_log(f"Request : {request}")

        # TODO: handle request

        response = HeartbeatResp({
            'status':RespStatus.SUCCESS.value,
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

        stable_vars = self.stable_storage.load()

        response = ApplyMembershipResp({
            "status":            "success",
            "log":               stable_vars["log"], # FIXME: log terbaru apa semua? yang terbaru aja
            "cluster_addr_list": self.cluster_addr_list,
        })
        return self.msg_parser.serialize(response)

    def execute(self, json_request: str) -> str:
        request: ExecuteReq = self.msg_parser.deserialize(json_request)
        # TODO : Implement execute
        response = ExecuteResp({})
        return self.msg_parser.serialize(response)
