from typing import TypedDict, List, Set, Dict
from Address import Address
from structs.Log import Log

class ClusterElmt(TypedDict):
  addr: Address
  sent_length: int
  acked_length: int

class NodeStatus(TypedDict):
  address: Address
  election_term: int
  voted_for: Address     
  log: List[Log] 
  commit_length: int
  type: str
  cluster_leader_addr: Address
  votes_received: List[Address]
  cluster_elmts: Dict[str, ClusterElmt]
