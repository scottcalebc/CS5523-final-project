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
        if not request.IsInitialized():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Fields missing from message")
        
        if len(request.ipAddress) == 0 or request.port == 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Cannot contain empty ip address or port")

        identical_list = list(filter(lambda x: x.ipAddress == request.ipAddress and x.port == request.port, self.server_ips))
        same_ids = list(filter(lambda x: x.id == request.id, identical_list))
        if len(identical_list) > 0 and len(identical_list) != len(same_ids):
            context.abort(grpc.StatusCode.ALREADY_EXISTS, "Object with that address and port already exist on system")

        same_ids = list(filter(lambda x: x.id == request.id, self.server_ips))
        if len(same_ids) > 1:
            for x in same_ids:
                self.server_ips.pop(self.server_ips.index(same_ids))
            context.abort(grpc.StatusCode.OUT_OF_RANGE, "Error multiple servers with same ID clearing out all servers")
            
        if len(same_ids) == 1:
            self.server_ips.pop(self.server_ips.index(same_ids[0]))

        print(f"{self.comp_name} : Registering server at {request.ipAddress}")


        self.server_ips.append(request)


        print(f"All chatservers: {self.server_ips}")

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
    server.add_insecure_port('127.0.0.1:' + str(port))
    server.start()

    server.wait_for_termination()


