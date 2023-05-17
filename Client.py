import sys
from Address import Address
from xmlrpc.client import ServerProxy
from typing import List
from msgs.ExecuteMsg import ExecuteReq, ExecuteResp
from utils.MsgParser import MsgParser
from utils.RPCHandler import RPCHandler


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("client.py <server ip> <server port>")

    rpc_handler = RPCHandler()
    server_addr = Address(sys.argv[1], int(sys.argv[2]))
    while True:
        inp = input("Enter command: ").split()
        if inp[0] == "exit":
            break
        else:
            req = ExecuteReq({
                "command": inp[0],
                "value": " ".join(inp[1:])
            })
            resp = rpc_handler.request(server_addr, "execute", req)
            print(resp)