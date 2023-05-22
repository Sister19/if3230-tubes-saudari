from utils.MsgParser import MsgParser
from msgs.BaseMsg import BaseMsg, BaseResp, RespStatus
from msgs.ErrorMsg import ErrorResp
import json
from Address import Address
from xmlrpc.client import ServerProxy


class RPCHandler:
    def __init__(self, id: str | None = None):
        self.msg_parser = MsgParser()
        self.id = id

    def __print_log(self, msg: str):
        print(f"[RPCHandler-{self.id}] {msg}")

    def __call(self, addr: Address, rpc_name: str, msg: BaseMsg):
       
        try:
            node = ServerProxy(f"http://{addr.ip}:{addr.port}")
            if isinstance(node, ConnectionRefusedError):
                raise Exception(f"Node {addr.ip}:{addr.port} can't be reached")
            json_request = self.msg_parser.serialize(msg)
            self.__print_log(f"Sending request to {addr.ip}:{addr.port}...")
            rpc_function = getattr(node, rpc_name)

            response = rpc_function(json_request)

            if isinstance(response, ConnectionRefusedError):
                raise Exception(f"Node {addr.ip}:{addr.port} can't be reached")
            elif isinstance(response, TimeoutError):
                raise Exception(f"Node {addr.ip}:{addr.port} timeout")
            elif isinstance(response, TypeError):
                raise Exception(f"Node {addr.ip}:{addr.port} return invalid response")
            
            self.__print_log(f"Response from {addr.ip}:{addr.port}: {response}")
            return response
        except Exception as e:
            self.__print_log(f"Error while sending request to {addr.ip}:{addr.port}: {e}")
            # print(e.with_traceback(True))
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
            self.__print_log("Failed to send request")
            # exit(1)
            # raise Exception(response["error"])

        response["address"] = redirect_addr
        return response
