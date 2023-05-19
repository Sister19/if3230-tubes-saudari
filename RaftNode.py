import asyncio
from threading import Thread
from xmlrpc.client import ServerProxy
from typing import Any, List, Set, Dict
from enum import Enum
from Address import Address
import socket
import time
from msgs.ApplyMembershipMsg import ApplyMembershipReq, ApplyMembershipResp
from msgs.BaseMsg import BaseMsg
from msgs.HeartbeatMsg import HeartbeatResp, HeartbeatReq
from msgs.ExecuteMsg import ExecuteReq, ExecuteResp
from utils.MsgParser import MsgParser
from structs.Log import Log
from msgs.VoteMsg import VoteReq, VoteResp
from msgs.AddLogMsg import AddLogReq, AddLogResp
from msgs.CommitLogMsg import CommitLogReq, CommitLogResp
from msgs.BaseMsg import BaseReq, BaseResp, RespStatus
from typing import TypedDict, TypeVar, Generic
from msgs.ErrorMsg import ErrorResp
from utils.RPCHandler import RPCHandler
import json
import math
import random
from utils.time import ResettableInterval

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
        APPEND_LOG = "append_log"
        COMMIT_LOG = "commit_log"
    
    class StableVars(TypedDict):
        election_term: int
        voted_for: Address     
        log: List[Log] 
        commit_length: int


    # Heeh, semua yang diatas dari komen ini

    class ClusterElmt(TypedDict):
        addr: Address
        sent_length: int
        acked_length: int

    class LstVars:
        map: Dict[str, "RaftNode.ClusterElmt"]

        def __init__(self):
            self.map = {}

        def append_addr(self, addr: Address):
            id = str(addr)
            new_elmt = RaftNode.ClusterElmt(addr=addr, sent_length=0, acked_length=0)
            self.map[id] = new_elmt

        def ids(self):
            return list(self.map.keys())
        
        def len(self):
            return len(self.map)
        
        def elmt(self, id: str):
            return self.map[id]

        def store(self, id: str, elmt: "RaftNode.ClusterElmt"):
            self.map[id] = elmt
            return self.map[id]
        
        def copy_addrs(self):
            return [x["addr"] for x in self.map.values()]
        
        def set_addrs(self, addrs: List[Address]):
            self.map = {}
            for addr in addrs:
                self.append_addr(addr)

    address: Address
    app: Any
    msg_parser: MsgParser
    rpc_handler: RPCHandler
    stable_storage: StableStorage[StableVars]
    type: NodeType
    cluster_leader_addr : Address
    lst_vars: LstVars
    votes_received: Set[Address]

    def __init__(self, application: Any, addr: Address, contact_addr: Address = None):
        socket.setdefaulttimeout(RaftNode.RPC_TIMEOUT)
        self.address:             Address = addr
        self.app:                 Any = application

        # volatile vars
        self.__init_volatile()

        # stable storage vars
        self.__try_fetch_stable()

        # additional vars
        self.msg_parser: MsgParser = MsgParser()
        self.rpc_handler: RPCHandler = RPCHandler()

        self.election_timeout = random.randrange(
            RaftNode.ELECTION_TIMEOUT_MIN, RaftNode.ELECTION_TIMEOUT_MAX)

        if contact_addr is None:
            self.lst_vars.append_addr(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)
        
        self.__init_heartbeat()
        self.__init_timeout()

    def __callback_election_interval(self):
        self.__print_log("callback election interval")
        if self.type == RaftNode.NodeType.LEADER:
            self.__print_log("leader, cancel election timeout")
            self.timeout = False
            return

        if not self.timeout:
            self.__print_log("not timeout, reset election timeout")
            self.timeout = True
            return

        # TODO: confirm
        self.__print_log("timeout, request vote")
        self.__req_vote()

    def __cancel_election_timeout(self):
        self.timeout = False
        self.election_interval.reset()

    def __init_timeout(self):
        self.timeout = False
        self.election_interval = ResettableInterval(
            self.election_timeout,
            self.__callback_election_interval
        )
        self.election_interval.start()
        #set_interval(
            #self.__callback_election_interval, self.election_timeout)

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
        self.votes_received: Set[Address] = set[Address]()
        self.lst_vars = RaftNode.LstVars()


    def __req_vote(self):
        self.__print_log("Request votes")
        stable_vars = self.stable_storage.load()

        stable_vars = self.stable_storage.update('election_term', stable_vars['election_term'] + 1)
        stable_vars = self.stable_storage.update('voted_for', self.address) # FIXME: voted_for = leader_addr? ato beda? bisa disamain kok
        self.type = RaftNode.NodeType.CANDIDATE
        self.votes_received = set[Address]()
        self.votes_received.add(str(self.address))
        
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

        for id in self.lst_vars.ids():
            self.__print_log(f"Sending request vote to {id}")
            elmt = self.lst_vars.elmt(id)
            # TODO: make sure async
            asyncio.run(self.__try_request_vote(elmt["addr"], msg))

        # TODO: start timer
        # TODO: pindahin start timer ke sini

    async def __try_request_vote(self, addr_dest: Address, msg: VoteReq):
        response: VoteResp = self.rpc_handler.request(
            addr_dest,
            RaftNode.FuncRPC.REQUEST_VOTE.value,
            msg,
        )

        self.__print_log(f"__try_request_vote.response: {response}")

        voter_id = response["node_addr"]
        voter_term = response["current_term"]
        granted = response["granted"]

        stable_vars = self.stable_storage.load()

        if self.type == RaftNode.NodeType.CANDIDATE and stable_vars["election_term"] == voter_term and granted:
            self.votes_received.add(str(voter_id))
            if len(self.votes_received) >= (self.lst_vars.len() + 1) / 2:
                self.__initialize_as_leader()
                # TODO: cancel election timer
                self.__cancel_election_timeout()
                # TODO: replicate log for all cluster nodes
        elif voter_term > stable_vars["election_term"]:
            stable_vars["election_term"] = voter_term
            stable_vars["voted_for"] = None
            self.stable_storage.storeAll(stable_vars)

            self.type = RaftNode.NodeType.FOLLOWER
            # TODO: cancel election timer
            self.__cancel_election_timeout()        
    
    def request_vote(self, json_request: str):
        request: VoteReq = self.msg_parser.deserialize(json_request)
        self.__print_log(f"request vote: {request}")

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
            response["granted"] = True
        else:
            response["granted"] = False
        
        self.__print_log(f"response vote: {response}")
        return self.msg_parser.serialize(response)
        

    def __print_log(self, text: str): # FIXME: Plis jangan print_log gua kira ngeprint isi log
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] [{self.type}] {text}")

    def __init_heartbeat(self):
        # TODO : Inform to all node this is new leader
        self.heartbeat_thread = Thread(target=asyncio.run, args=[ #FIXME: berarti klo bukan leader, thread loopnya beda lagi?
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address # FIXME: cluster_leader_addr = voted_for? ato beda? bisa disamain kok
        self.type = RaftNode.NodeType.LEADER

    async def __leader_heartbeat(self):
        # TODO : Send periodic heartbeat
        while True:
            if self.type == RaftNode.NodeType.LEADER:
                self.__print_log("Sending heartbeat...")
                pass # FIXME: WHaat?

                # TODO : Send heartbeat to all node
                for id in self.lst_vars.ids():
                    elmt = self.lst_vars.elmt(id)
                    addr = elmt["addr"]

                    if addr == self.address:
                        continue

                    stable_vars = self.stable_storage.load()

                    prefix_len = elmt["sent_length"]
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
                    
                    resp: HeartbeatResp = self.rpc_handler.request(
                        addr,
                        RaftNode.FuncRPC.HEARTBEAT.value,
                        msg,
                    )

                    resp_term = resp["term"]
                    ack = resp["ack"]
                    success_append = resp["success_append"]

                    acked_len = elmt["acked_length"]

                    stable_vars = self.stable_storage.load()

                    if resp_term == stable_vars["election_term"] and self.type == RaftNode.NodeType.LEADER:
                        if success_append and ack >= acked_len:
                            elmt["sent_length"] = ack
                            elmt["acked_length"] = ack
                            self.lst_vars.store(id, elmt)
                            self.__commit_log_entries()
                        elif elmt["sent_length"] > 0: #self.lst_vars.sent_length(follower_idx) > 0:
                            elmt["sent_length"] = elmt["sent_length"] - 1
                            self.lst_vars.store(id, elmt)

                            # TODO: REPLICATE LOG
                    elif resp_term > stable_vars["election_term"]:
                        stable_vars["election_term"] = resp_term
                        stable_vars["voted_for"] = None
                        self.stable_storage.storeAll(stable_vars)
                        self.type = RaftNode.NodeType.FOLLOWER
                        # TODO: cancel election timer
                        self.__cancel_election_timeout()
                        break

            await asyncio.sleep(RaftNode.HEARTBEAT_INTERVAL)

    def __try_to_apply_membership(self, contact_addr: Address):
        msg = ApplyMembershipReq(self.address)
        self.__print_log(f"Sending msg : {msg}")
        response: ApplyMembershipResp = self.rpc_handler.request(
            contact_addr, RaftNode.FuncRPC.APPLY_MEMBERSHIP.value, msg)
        
        # TODO: handle failed response
        self.__print_log(f"Response : {response}")
        self.stable_storage.update("log", response["log"])
        # self.cluster_addr_list = response["cluster_addr_list"]
        self.lst_vars.set_addrs(response["cluster_addr_list"])
        self.cluster_leader_addr = response["address"]

    # Inter-node RPCs
    def heartbeat(self, json_request: str) -> str:
        # TODO : Implement heartbeat, reappend log baru dan check commitnya juga
        request: HeartbeatReq = self.msg_parser.deserialize(json_request)
        self.__print_log(f"Request : {request}")

        leader_addr = request["leader_addr"]
        req_term = request["term"]
        prefix_len = request["prefix_len"]
        prefix_term = request["prefix_term"]
        leader_commit = request["commit_length"]
        suffix = request["suffix"]

        stable_vars = self.stable_storage.load()

        if req_term > stable_vars["election_term"]:
            stable_vars["election_term"] = req_term
            stable_vars["voted_for"] = None
            stable_vars = self.stable_storage.storeAll(stable_vars)
            
            # TODO: cancel election timer
            self.__cancel_election_timeout()
        
        if req_term == stable_vars["election_term"]:
            self.type = RaftNode.NodeType.FOLLOWER
            self.cluster_leader_addr = leader_addr
        
        log = stable_vars["log"]
        log_ok = (
            (len(log) >= prefix_len) and 
            (prefix_len == 0 or log[prefix_len - 1]["term"] == prefix_term))
        
        response = HeartbeatResp({
            'status': RespStatus.SUCCESS.value,
            "heartbeat_response": "ack",
            "address":            self.address,
            "term": stable_vars["election_term"],
        })

        if req_term == stable_vars["election_term"] and log_ok:
            self.__append_entries(prefix_len, leader_commit, suffix)
            ack = prefix_len + len(suffix)
            response["ack"] = ack
            response["success_append"] = True
        else:
            response["ack"] = 0
            response["success_append"] = False

        return self.msg_parser.serialize(response)
    
    def __append_entries(self, prefix_len: int, leader_commit: int, suffix: List[Log]):
        stable_vars = self.stable_storage.load()
        log = stable_vars["log"]

        if len(suffix) > 0 and len(log) > prefix_len:
            idx = min(len(log), prefix_len + len(suffix)) - 1
            if log[idx]["term"] != suffix[idx - prefix_len]["term"]:
                log = log[:prefix_len] # TODO: confirm
        
        if prefix_len + len(suffix) > len(log):
            for i in range(len(log) - prefix_len, len(suffix)):
                log.append(suffix[i])
        
        stable_vars["log"] = log
        stable_vars = self.stable_storage.storeAll(stable_vars)

        commit_length = stable_vars["commit_length"]
        if leader_commit > commit_length:
            for i in range(commit_length, leader_commit):
                # TODO: deliver log to application
                pass
            stable_vars["commit_length"] = leader_commit
            stable_vars = self.stable_storage.storeAll(stable_vars)
    
    def __calc_num_ack(self, idx: int):
        num_acked = 0
        for id in self.lst_vars.ids():
            elmt = self.lst_vars.elmt(id)
            if elmt["acked_length"] >= idx:
                num_acked += 1

        return num_acked

    def __commit_log_entries(self):
        min_acks = math.ceil((self.lst_vars.len() + 1) / 2)
        stable_vars = self.stable_storage.load()

        log = stable_vars["log"]
        if (len(log) == 0):
            return

        acked_above_threshold = [
            self.__calc_num_ack(x) >= min_acks
            for x in range(len(log))
        ]
        latest_ack = -1
        # iterate in reverse order
        for i in range(len(log) - 1, -1, -1):
            if acked_above_threshold[i]:
                latest_ack = i
                break
        
        commit_length = stable_vars["commit_length"]
        last_log_term = log[latest_ack]["term"]
        election_term = stable_vars["election_term"]
        if (latest_ack != -1 
            and latest_ack > commit_length
            and last_log_term == election_term):
            for i in range(commit_length, latest_ack):
                # TODO: DELIVER LOG TO APP
                pass
        
            self.stable_storage.update("commit_length", latest_ack)


    def append_log(self, json_request: str) -> str:
        request = self.msg_parser.deserialize(json_request)
        log = Log({
            "term": request["term"],
            "command": request["command"],
            "value": request["value"],
            "is_committed": False
        })

        stable_vars = self.stable_storage.load()
        stable_vars["log"].append(log)
        self.stable_storage.update("log", stable_vars["log"])

        response = AddLogResp({
            "status": RespStatus.SUCCESS.value,
            "address": self.address,
        })

        return self.msg_parser.serialize(response)
    
    def commit_log(self, json_request: str) -> str:
        request = self.msg_parser.deserialize(json_request)
        
        stable_vars = self.stable_storage.load()
        for i in range(stable_vars["commit_length"], request["commit_length"]):
            self.__print_log(f"Committing log {i}")
            # Execute Command

        stable_vars["commit_length"] = request["commit_length"]
        self.stable_storage.update("commit_length", stable_vars["commit_length"])

        response = CommitLogResp({
            "status": RespStatus.SUCCESS.value,
            "address": self.address,
        })

        return self.msg_parser.serialize(response)

    # Client RPCs
    def apply_membership(self, json_request: str) -> str: #FIXME: apply membership pake consensus, dan blocking 1 persatu
        # TODO : Implement apply_membership
        request = self.msg_parser.deserialize(json_request)
        self.__print_log(f"Request : {request}")
        # TODO: notify existing nodes
        self.lst_vars.append_addr(Address(request["ip"], request["port"]))

        stable_vars = self.stable_storage.load()

        response = ApplyMembershipResp({
            "status":            "success",
            "log":               stable_vars["log"], # FIXME: log terbaru apa semua? yang terbaru aja
            "cluster_addr_list": self.lst_vars.copy_addrs(),
        })
        return self.msg_parser.serialize(response)

    def execute(self, json_request: str) -> str:
        request: ExecuteReq = self.msg_parser.deserialize(json_request)
        
        # FIXME: VOTES_RECEIVED should be set of address, not int
        # in order to avoid different response from same node
        # eg: duplicate vote from same node
        # FIXME: VOTES_RECEIVED represent number of election votes
        # not number of ack from append log
        self.votes_received = 0
        stable_vars = self.stable_storage.load()

        log = Log({
            "term": stable_vars["election_term"],
            "command": request["command"],
            "value": request["value"],
        })

        stable_vars["log"].append(log)
        self.stable_storage.update("log", stable_vars["log"])

        # TODO: EVENT MANAGEMENT
        self.wait_for_votes = asyncio.Event()

        # for i in range(self.lst_vars.len()):
        #     addr = self.lst_vars.cluster_addr_list(i)
        for id in self.lst_vars.ids():
            elmt = self.lst_vars.elmt(id)
            addr = elmt["addr"]

            if addr == self.address:
                continue
            asyncio.create_task(self.__send_append_log(addr, log))

        async def wait_for_votes():
            await self.wait_for_votes.wait()

        if self.lst_vars.len() > 1:
            asyncio.get_event_loop().run_until_complete(wait_for_votes())


        # TODO: Execute Command
        stable_vars["commit_length"] += 1
        self.stable_storage.update("commit_length", stable_vars["commit_length"])

        # for addr in self.cluster_addr_list:
        # for i in range(self.lst_vars.len()):
        #     addr = self.lst_vars.cluster_addr_list(i)
        for id in self.lst_vars.ids():
            elmt = self.lst_vars.elmt(id)
            addr = elmt["addr"]

            if addr == self.address:
                continue
            asyncio.create_task(self.__send_commit_log(addr, stable_vars["commit_length"]))            

        response = ExecuteResp({
            "status": RespStatus.SUCCESS.value,
            "address": self.address,
        })
        return self.msg_parser.serialize(response)
    
    async def __send_append_log(self, addr: Address, log: Log):
        msg = AddLogReq({
            "term": log["term"],
            "command": log["command"],
            "value": log["value"],
        })
        response: AddLogResp = self.rpc_handler.request(
            addr, RaftNode.FuncRPC.APPEND_LOG.value, msg)
        
        if (response["status"] == RespStatus.SUCCESS.value):
            self.votes_received += 1
            if self.votes_received >= (self.lst_vars.len() // 2 + 1):
                self.wait_for_votes.set()
        
    async def __send_commit_log(self, addr: Address, commit_length: int):
        stable_vars = self.stable_storage.load()
        msg = CommitLogReq({
            commit_length: stable_vars["commit_length"],
        })
        self.rpc_handler.request(
            addr, RaftNode.FuncRPC.COMMIT_LOG.value, msg)
