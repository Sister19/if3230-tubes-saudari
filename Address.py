from typing import TypedDict

class AddressData(TypedDict):
    ip: str
    port: int

class Address(dict):
    def __init__(self, ip: str, port: int):
        dict.__init__(self, ip=ip, port=port)
        self.ip = ip
        self.port = port

    def __str__(self):
        return str(self.__dict__)

    def __iter__(self):
        return iter((self.ip, self.port))

    def __eq__(self, other: "Address"):
        return self["ip"] == other["ip"] and self["port"] == other["port"]

    def __ne__(self, other: "Address"):
        return self["ip"] != other["ip"] or self["port"] != other["port"]

    def data(self) -> AddressData:
        return AddressData(ip=self.ip, port=self.port)
