import asyncio
from Address import Address
from utils.RPCHandler import RPCHandler
import socket
from msgs.GetClusterMsg import GetClusterResp
from msgs.GetStatusMsg import GetStatusResp
import json
from flask import Flask, request
from flask_cors import CORS
from typing import List

app = Flask(__name__)
CORS(app)

def req_status_node(addr: Address):
    rpc_handler = RPCHandler()
    resp: GetStatusResp = rpc_handler.request(addr, "get_status", {})
    return resp

async def async_req_status_node(addr: Address):
    return await asyncio.to_thread(req_status_node, addr)

async def get_statuses(ip: str, port: int):
    addr = Address(ip, port)
    rpc_handler = RPCHandler()
    resp: GetClusterResp = rpc_handler.request(addr, "get_cluster", {})
    cluster_elmts = resp["data"]

    print("cluster_elmts",cluster_elmts)

    statuses: List[GetStatusResp] = await asyncio.gather(*[async_req_status_node(x["addr"]) for x in cluster_elmts])
    print("statuses",statuses)

    return [x["data"] for x in statuses]


@app.route('/cluster', methods=["GET"])
async def slash():
    args = request.args
    ip = args.get("ip", default="localhost", type=str)
    port = args.get("port", default=5000, type=int)

    print("ip", ip)
    print("port", port)

    res = await get_statuses(ip, port)
    return json.dumps(res)

if __name__ == '__main__':
   app.run(host="localhost", port=8080, debug=True)
