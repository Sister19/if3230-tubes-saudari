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

class RaftNode:
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

    def __init__(self, application: Any, addr: Address, contact_addr: Address = None):
        socket.setdefaulttimeout(RaftNode.RPC_TIMEOUT)
        self.address:             Address = addr
        self.type:                RaftNode.NodeType = RaftNode.NodeType.FOLLOWER
        self.log:                 List[str] = []
        self.app:                 Any = application
        self.election_term:       int = 0
        self.cluster_addr_list:   List[Address] = []
        self.cluster_leader_addr: Address = None
        self.msg_parser: MsgParser = MsgParser()
        if contact_addr is None:
            self.cluster_addr_list.append(self.address)
            self.__initialize_as_leader()
        else:
            self.__try_to_apply_membership(contact_addr)

    # Internal Raft Node methods

    def __print_log(self, text: str):
        print(f"[{self.address}] [{time.strftime('%H:%M:%S')}] {text}")

    def __initialize_as_leader(self):
        self.__print_log("Initialize as leader node...")
        self.cluster_leader_addr = self.address
        self.type = RaftNode.NodeType.LEADER
        request = {
            "cluster_leader_addr": self.address
        }
        # TODO : Inform to all node this is new leader
        self.heartbeat_thread = Thread(target=asyncio.run, args=[
                                       self.__leader_heartbeat()])
        self.heartbeat_thread.start()

    async def __leader_heartbeat(self):
        # TODO : Send periodic heartbeat
        while True:
            self.__print_log("[Leader] Sending heartbeat...")
            pass
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
        # TODO : Implement heartbeat
        response = HeartbeatResp({
            "heartbeat_response": "ack",
            "address":            self.address,
        })
        return self.msg_parser.serialize(response)

    # Client RPCs
    def apply_membership(self, json_request: str) -> str:
        # TODO : Implement apply_membership
        request = self.msg_parser.deserialize(json_request)
        print(f"Request : {request}")
        self.cluster_addr_list.append(Address(request["ip"], request["port"]))
        response = ApplyMembershipResp({
            "status":            "success",
            "log":               self.log,
            "cluster_addr_list": self.cluster_addr_list,
        })
        return self.msg_parser.serialize(response)

    def execute(self, json_request: str) -> str:
        request: ExecuteReq = self.msg_parser.deserialize(json_request)
        # TODO : Implement execute
        response = ExecuteResp({})
        return self.msg_parser.serialize(response)
