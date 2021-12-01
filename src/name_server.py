from concurrent import futures

import threading
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
        
        
        self.server_lock = threading.Lock()
        self.server_ips = []
        self.server_group_map = {}
        self.server_id_map = {}

    def notifyDisconnect(self, request: msg.RegisterServer, context):
        print(f"Received a disconnect event of a chatServer")

        with self.server_lock:
            # remove server from list
            server_obj = self.server_id_map.get(request.id, None)
            print(f"Found server object: {server_obj}")
            if server_obj == None:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Server with that id not attached to chat system")

            print(f"Testing if server reconnected after client attempts to notify system")
            if len(server_obj.timestamp.ListFields()) > 0 and len(request.timestamp.ListFields()) > 0:
                server_obj_date = server_obj.timestamp.ToDatetime()
                request_date = request.timestamp.ToDatetime()

                print(f"Comparing dates {server_obj_date} and {request_date}")
                if request_date < server_obj_date:
                    print("Server object newer")
                    context.set_detail("Not removing server object as object updated before request time")
                    return global_msg.Empty()

            print("Clearing id map of object id")
            self.server_id_map[request.id] == None
        
            print("Removing server from server list")

            try:
                self.server_ips.pop(self.server_ips.index(server_obj))
            except ValueError as e:
                context.set_details("Server was not in IP list? Could it have been set somewhere else?")
                
            
            group = None
            print("Finding server - group mapping")
            for g, s in self.server_group_map.items():
                print(f"Testing is group ({g}) sever {s} is the same as {request}")
                if s.id == request.id:
                    group = g
            
            # reassign group to new chatServer
            print("Reassigning group")
            if group != None:
                sys = random.choice(self.server_ips)
                print(f"Giving group {g} server {sys}")
                self.server_group_map[group] = sys
            
        return global_msg.Empty()



    def getChannel(self, request: global_msg.Group, context):
        print(f"Receving request from client interface with msg: {request}")
        if len(request.name) == 0:
            request.name = "all"

        with self.server_lock:
            print("Obtained server lock to retrieve server for client")
            if len(self.server_ips) == 0:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, "No Chat Servers available")

            print(f"Servers avilable attempting to find a server for group: {request.name}")
            if self.server_group_map.get(request.name, None) == None:
                print("No server for group, finding new server")
                sys = random.choice(self.server_ips)
                print(f"Found server with details: {sys}")
                self.server_group_map[request.name] = sys
            else:
                sys = self.server_group_map[request.name]
                print(f"Server available for {request.name} : {sys}")
                        
            print(f"{self.comp_name} : Request from {request.name} returning {sys}")
            sys.status = 1

            return sys

    def registerChatServer(self, request: msg.RegisterServer, context):
        if not request.IsInitialized():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Fields missing from message")
        
        if len(request.ipAddress) == 0 or request.port == 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Cannot contain empty ip address or port")

        if len(request.id) == 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Must supply and ID for the chat server")

        # add or modify list while holding lock
        with self.server_lock:
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
            self.server_id_map[request.id] = request


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


