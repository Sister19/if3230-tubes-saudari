from utils.MsgParser import MsgParser
from msgs.BaseMsg import BaseMsg, BaseResp, RespStatus
from msgs.ErrorMsg import ErrorResp
import json
from Address import Address
from xmlrpc.client import ServerProxy


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
            # raise Exception(response["error"])

        response["address"] = redirect_addr
        return response
