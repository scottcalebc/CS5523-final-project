from concurrent import futures
import argparse
import grpc
import time

"""
    Using random funciton to select from list,
    eventually move to keeping state of systems 
    and which groups they serve
"""
import random

import interfaces.globalmessage_pb2 as global_msg

import interfaces.nameservice_pb2 as msg
import interfaces.nameservice_pb2_grpc as rpc


class NameServer(rpc.NameServerServicer):

    def __init__(self):
        self.comp_name = "NameServer"
        self.server_ips = []

    def getChannel(self, request: global_msg.Group, context):
        print(f"Receving request from client interface")
        if len(self.server_ips) == 0:
            reply = msg.RegisterServer()
            reply.status = 3
            return reply

        sys = random.choice(self.server_ips)
        print(f"{self.comp_name} : Request from {request.name} returning {sys}")
        sys.status = 1
        return sys

    def registerChatServer(self, request: msg.RegisterServer, context):
        print(f"{self.comp_name} : Registering server at {request.ipAddress}")
        self.server_ips.append(request)

        return global_msg.Empty()


def parse_args():
    parser = argparse.ArgumentParser(description="NameSevice for the distributed chat system")
    parser.add_argument("--port", action="store", type=str)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    if args.port == None:
        port = 3535
    else:
        port = args.port

    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rpc.add_NameServerServicer_to_server(NameServer(), server)

    print("Starting server. Listening...")
    server.add_insecure_port('[::]:' + str(port))
    server.start()

    while True:
        time.sleep(64*64*100)


