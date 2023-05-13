import asyncio
from threading import Thread
from xmlrpc.client import ServerProxy
from typing import Any, List, TypedDict, Tuple, Optional
from enum import Enum
from enums.Command import Command
from Address import Address
import socket
import time
from structs.Log import Log

HEARTBEAT_INTERVAL = 1
ELECTION_TIMEOUT_MIN = 2
ELECTION_TIMEOUT_MAX = 3
RPC_TIMEOUT = 0.5


class NodeType(Enum):
    LEADER = 1
    CANDIDATE = 2
    FOLLOWER = 3


class FuncRPC(Enum):
    HEARTBEAT = "heartbeat"


class NodeData(TypedDict):
    address: Address
    last_sent_index: int


class RaftNode:
    app: Any = None

    state: NodeType
    term: int

    log: List[Log]
    commit_index = property(
        lambda self: [log.index for log in self.log if log.is_committed][-1]
        if len(self.log) > 0
        else 0
    )
    last_index = property(
        lambda self: self.log[-1].index if len(self.log) > 0 else 0
    )

    address: Address
    leader_address: Address

    clusters: List[NodeData]  # Exclude dirinya sendiri
    cluster_size = property(lambda self: len(self.clusters) + 1)

    def __init__(
        self, application: Any, addr: Address, contact_addr: Address = None
    ):
        socket.setdefaulttimeout(RPC_TIMEOUT)
        self.address: Address = addr
        self.app: Any = application

        # stable storage vars
        self.__try_fetch_stable()

        # volatile vars
        self.__init_volatile()

        if not contact_addr is None:
            # Try to get membership from contact_addr
            try:
                leader_address, clusters = self.__try_to_apply_membership(
                    contact_addr
                )
                self.leader_address = leader_address
                self.clusters = clusters
            except:
                pass

        # initialize loop
        self.__init_loop()

    def __on_recover_crash(self):
        self.__try_fetch_stable()
        self.__init_volatile()

    def __try_fetch_stable(self):
        # TODO: get stable storage
        # if exist persistence, get persistence, return

        self.__init_stable()

    def __init_stable(self):
        self.term: int = 0
        self.log = []
        clusters = []

    def __init_volatile(self):
        self.state = NodeType.FOLLOWER
        self.cluster_leader_addr: Address = None

    def __try_to_apply_membership(
        self, contact_addr: Address
    ) -> Tuple[Address, List[NodeData]]:
        proxy = ServerProxy(f"http://{contact_addr.ip}:{contact_addr.port}")
        leader_address, clusters = proxy.apply_membership(self.address)
        return leader_address, clusters

    # LOOPS
    def __init_loop(self):
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.__loop())

    def __interrupt_and_restart_loop(self):
        self.loop.stop()
        self.loop.close()
        self.__init_loop()

    async def __loop(self):
        while True:
            if self.state == NodeType.LEADER:
                self.__leader_loop()
            elif self.state == NodeType.FOLLOWER:
                self.__follower_loop()
            elif self.state == NodeType.CANDIDATE:
                self.__candidate_loop()

    # LEADER FUNCTIONS
    def __leader_loop(self):
        # Send heartbeat to all nodes asynchronously (in parallel)
        for node in self.clusters:
            asyncio.create_task(self.__send_heartbeat(node))
        asyncio.sleep(HEARTBEAT_INTERVAL)

    async def __send_heartbeat(self, node: NodeData):
        new_logs = self.log[node.last_sent_index + 1 :]
        last_sent_index = self.__call_rpc(
            node.address, FuncRPC.HEARTBEAT, self.address, self.term, new_logs
        )
        if not last_sent_index is None:
            node.last_sent_index = last_sent_index  # FIXME: takut gak work assign lewat async reference

    # FOLLOWER FUNCTIONS
    def __follower_loop(self):
        pass

    # CANDIDATE FUNCTIONS
    def __candidate_loop(self):
        pass

    # LOG FUNCTIONS
    def __revert_log(self, index: int):
        self.log.pop(index)

    # COMMAND FUNCTIONS
    def __execute_command(self, command: str, value: str):
        pass

    def __enqueue(self, value: str):
        pass

    def __dequeue(self) -> str:
        pass

    # RPC FUNCTIONS
    def __call_rpc(self, addr: Address, func: FuncRPC, *args) -> Any:
        try:
            proxy = ServerProxy(f"http://{addr.ip}:{addr.port}")
            return getattr(proxy, func.value)(*args)
        except:
            # TODO: Print error
            return None

    def heartbeat(
        self, from_addr: Address, term: int, new_logs: List[Log]
    ) -> int:
        if term <= self.term:
            raise Exception("Term is not greater than current term")

        if len(new_logs) > 0:
            if new_logs[0]["index"] == len(self.log):
                self.log += new_logs
            elif new_logs[0]["index"] > len(self.log):
                self.log = self.log[: new_logs[0]["index"]] + new_logs
            else:
                raise Exception("Log index is not greater than current index")

            # Commit previous logs if new_logs has committed logs
            if new_logs[0]["is_committed"]:
                for log in self.log:
                    if not log["is_committed"]:
                        break
                    log["is_committed"] = True
                    self.__execute_command(log["command"], log["value"])

        self.term = term
        self.state = NodeType.FOLLOWER
        self.leader_address = from_addr

        self.__interrupt_and_restart_loop()
        return self.last_index
