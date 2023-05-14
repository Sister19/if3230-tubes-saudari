from msgs.BaseMsg import BaseReq, BaseResp
from Address import AddressData

# TODO : class HeartbeatReq

class HeartbeatResp(BaseResp):
    heartbeat_response: str
    address: AddressData

