from msgs.BaseMsg import BaseMsg
from Address import AddressData

# TODO : class HeartbeatReq

class HeartbeatResp(BaseMsg):
    heartbeat_response: str
    address: AddressData

