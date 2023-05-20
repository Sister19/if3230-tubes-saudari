import asyncio
from Address import Address
from utils.RPCHandler import RPCHandler
import socket
from msgs.GetStatusMsg import GetStatusReq, GetStatusResp

from flask import Flask

app = Flask(__name__)


def request():
    socket.setdefaulttimeout(30)

    addr = Address("localhost", 5000)
    rpc_handler = RPCHandler()
    resp: GetStatusResp = rpc_handler.request(addr, "get_status", {})
    # print(resp)

    # cluster_leader_addr = resp["data"]["cluster_leader_addr"]
    # resp: GetStatusResp = rpc_handler.request(addr, "get_status", {})

    cluster_elmts = resp["data"]["cluster_elmts"]

    dict = {}
    for id in cluster_elmts:
        elmt = cluster_elmts[id]
        addr = elmt["addr"]
        resp: GetStatusResp = rpc_handler.request(addr, "get_status", {})
        dict[id] = resp
    
    return dict

@app.route('/')
def slash():
    return request()

        # print(resp)



# if __name__ == '__main__':
#     main()

if __name__ == '__main__':
   app.run(host="localhost", port=8080, debug=True)
