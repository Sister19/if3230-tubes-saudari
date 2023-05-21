import sys
from utils.RPCHandler import RPCHandler
from Address import Address
from msgs.ExecuteMsg import ExecuteReq, ExecuteResp

def main():
    if (len(sys.argv) < 5):
        print("one_cmd_client.py <server ip> <server port> <type> <command>")
        return

    rpc_handler = RPCHandler()

    ip = sys.argv[1]
    port = int(sys.argv[2])

    server_addr = Address(ip, port)

    type = sys.argv[3]

    if (type == "execute"):
        command = sys.argv[4]
        req = ExecuteReq({
            "command": command,
            "value": ""
        })

        resp: ExecuteResp = rpc_handler.request(server_addr, "execute", req)
        print(resp)
    
    elif (type == "request_log"):
        resp: ExecuteResp = rpc_handler.request(server_addr, "request_log", {})
        print(resp)


if __name__ == "__main__":
    main()
