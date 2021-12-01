from concurrent import futures

import grpc
import time
import uuid
import argparse
import threading

import helper_funcs

from google.protobuf.timestamp_pb2 import Timestamp

import interfaces.globalmessage_pb2 as global_msg

import interfaces.chatserver_pb2_grpc as rpc

import interfaces.nameservice_pb2 as ns_msg
import interfaces.nameservice_pb2_grpc as ns_rpc
from src.client import MAX_RETRIES, MAX_TIMEOUT


MAX_TIMEOUT = 5
MAX_RETRIES = 10



class ChatServer(rpc.ChatServerServicer):  # inheriting here from the protobuf rpc file which is generated

    def __init__(self):
        # List with all the chat history

        self.new_chat_event = threading.Event()
        self.chat_lock = threading.Lock()
        self.chats = {}
        self.chat_last_time = {}

        self.client_lock = threading.Lock()
        self.clients = {}

        # initilize event to set so first message will be written
        self.peer_receive_event = threading.Event()
        self.peer_receive_event.set()

    def GetHistory(self, request, context):
        print(f"GetHistory called by {context.peer()}")
        context.abort(grpc.StatusCode.UNIMPLEMENTED, "History unavailable")
########## I want to let the client knows the server is down.#######
    def Do(self, request, context):
        if not is_valid_field(request.field):
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('Consarnit!')
            ###I am not sure if the following is the correct destination proto file##
            return chatserver_pb2.Response()

        return chatserver_pb2.Response(response='Yeah!')
##################################################################
    # The stream which will be used to send new messages to clients
    def ChatStream(self, request: global_msg.Group, context):
        """
        This is a response-stream type call. This means the server can keep sending messages
        Every client opens this connection and waits for server to send new messages

        :param request_iterator:
        :param context:
        :return:
        """

        if not request.IsInitialized() and len(request.name) == 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Must specify a group to stream messages")
        
        
        peer = context.peer()
        print(f"Request for group {request.name} from peer {peer}")

        with self.chat_lock:
            print("Checking chat history")
            if self.chats.get(request.name, None) == None:
                print("Adding dictionary entry")
                self.chats[request.name] = None
                self.chat_last_time[request.name] = None
            
            with self.client_lock:
                print("Setting up peer information")
                if self.clients.get(request.name, None) == None:
                    print("Add dictionary for peer")
                    self.clients[request.name] = {}
                    self.clients[request.name]["received"] = 0
                else:
                    print("Add peer connection info and increment ")
                    
                    self.clients[request.name][peer] = 0
                    self.clients[request.name]["total"] = self.clients[request.name].get("total", 0) + 1

                print(self.clients[request.name])

        # lastindex = 0 if len(self.chats[request.name]) == 0 else len(self.chats[request.name])

        # For every client a infinite loop starts (in gRPC's own managed thread)
        print("Testing active context before streaming")
        while True:
            # Check if there are any new messages
            print("Waiting for new message event")
            self.new_chat_event.wait(MAX_TIMEOUT)
            if self.new_chat_event.is_set():
                with self.chat_lock:
                    print("Checking for new messages")
                    if self.chat_last_time == None or self.chat_last_time.get(request.name, None) == None:
                        # no new message
                        continue 
                    
                    # if self.chats[request.name].timestamp.ToDatetime() > self.chat_last_time[request.name].ToDatetime():
                    #     # chat message is newer, send to client

                    with self.client_lock:
                        
                        print("Checking if all peers have received message")
                        print(self.clients[request.name])
                        # if all clients received signal (may cause issue may signal numerous times, will return instantly if event is set)
                        if self.clients[request.name]["received"] == self.clients[request.name]["total"]:
                            print("Clearing chat event setting all peers received event")
                            self.new_chat_event.clear()
                            self.peer_receive_event.set()
                            continue 
                        
                        print("Checking if this peer has received this message already")
                        # if this client already received this message move on
                        if self.clients[request.name][peer] > 0:
                            continue

                        try:
                            print("Passing message to client")
                            yield self.chats[request.name]

                            print("Update peer informaiton since this peer will get info unless rpc excpetion occured")
                            self.clients[request.name][peer] = self.clients[request.name][peer] + 1
                            self.clients[request.name]["received"] = self.clients[request.name]["received"] + 1
                            print(self.clients[request.name])

                        except grpc.RpcError as e:
                            status = e.code()

                            print(f"Received rpc error when yielding message to client: {status}")
                            context.cancel()
                            # decrement total clients since 1 fell off
                            self.clients[request.name]["total"] = self.clients[request.name]["total"] - 1

                            break

                            # need to cleanup clients dict to remove peer information 
                            
        print("Context closed returning from call")



            # while len(self.chats[request.name]) > lastindex:
            #     n = self.chats[request.name][lastindex]
            #     lastindex += 1
            #     yield n

    def SendNote(self, request: global_msg.Note, context):
        """
        This method is called when a clients sends a Note to the server.

        :param request:
        :param context:
        :return:
        """
        # this is only for the server console
        if not request.IsInitialized() and not request.user.IsInitialized() and not request.group.IsInitialized():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Must initilize user and group information")

        if len(request.user.userName) == 0 or len(request.group.name) == 0:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Must include a username and group name")
        
        if not (request.timestamp.IsInitialized() and len( request.timestamp.ListFields() ) > 0):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "All messages require timestamp")
        print(request)
        print("[{} @ {}] {} in group {}".format(request.user.displayName, request.timestamp, request.message, request.group.name))
        # Add it to the chat history
        num_waits = 0
        print("Entering loop")
        while context.is_active():
            print("Waiting for peer event")
            self.peer_receive_event.wait(MAX_TIMEOUT)
            if self.peer_receive_event.is_set():
                print("Peer event set checking current message against chat queue")
                with self.chat_lock:
                    # if no chats exist then add to chat list
                    if self.chats.get(request.group.name, None) == None:
                        print("No new messages in queue, setting this message")
                        self.chats[request.group.name] = request
                        self.chat_last_time[request.group.name] = request.timestamp
                        print("Clear peer event set new chat event")
                        self.peer_receive_event.clear()
                        self.new_chat_event.set()
                        return global_msg.Empty()

                    # a chat message already exists
                    else:
                        print("Validating time of current message in queue with incoming message")
                        # if new message in past then inform client it needs to resend 
                        if self.chat_last_time[request.group.name].ToDatetime() > request.timestamp.ToDatetime():
                            context.abort(grpc.StatusCode.FAILED_PRECONDITION, "Message is too late in past resend")
                        # need to check peer receive information 
                        else: 
                            with self.client_lock:
                                print("Resetting peer information")
                                self.clients[request.group.name]["received"] = 0
                                # reset peer values
                                for peer, _ in self.clients[request.group.name].items():
                                    if peer != "received" and peer != "total":
                                        self.clients[request.group.name][peer] = 0
                                print(self.clients[request.group.name])

                                print("Setting new chat message")
                                self.chats[request.group.name] = request
                                self.chat_last_time[request.group.name] = request.timestamp

                                print("Clear peer receive and set new chat event")
                                self.peer_receive_event.clear()
                                self.new_chat_event.set()
                                return global_msg.Empty()

            num_waits = num_waits + 1

            if num_waits > MAX_RETRIES:
                context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "Clients took to long to respond to previous message")
        print("Context fell off")
                        




        # if self.chats.get(request.group.name, None) == None:
        #     self.chats[request.group.name] = []

        # if self.clients.get(request.user.userName, None) == None:
        #     group_index = len(self.chats[request.user.userName])
        #     self.clients[request.user.userName] = {request.group.name : group_index }
        # else:
        #     self.clients[request.user.userName][request.group.name] = len(self.chats[request.group.name])

        # self.chats[request.group.name].append(request)
        return global_msg.Empty()  # something needs to be returned required by protobuf language, we just return empty msg



def parse_args():
    parser = argparse.ArgumentParser(description="Chat Server for the distributed chat system")

    parser.add_argument("--port", action="store", type=int)
    parser.add_argument("--id", action="store", type=str)

    return parser.parse_args()
    
if __name__ == '__main__':
    port = 11915  # a random port for the server to run on
    id = str(uuid.uuid4())

    args = parse_args()

    if args.port != None:
        port = args.port
    
    if args.id != None:
        id = args.id
    # the workers is like the amount of threads that can be opened at the same time, when there are 10 clients connected
    # then no more clients able to connect to the server.
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))  # create a gRPC server
    rpc.add_ChatServerServicer_to_server(ChatServer(), server)  # register the server to gRPC
    # gRPC basically manages all the threading and server responding logic, which is perfect!
    print('Starting server. Listening...')
    server.add_insecure_port('127.0.0.1:' + str(port))
    

    # After starting server need to register with nameservice
    port_ns = 3535
    address_ns = '127.0.0.1'
    ns = grpc.insecure_channel(address_ns + ":" + str(port_ns))
    conn_ns = ns_rpc.NameServerStub(ns)

    registerMessage = ns_msg.RegisterServer()
    registerMessage.ipAddress = helper_funcs.get_ip()
    registerMessage.id = id
    registerMessage.port = port
    registerMessage.timestamp.GetCurrentTime()
    conn_ns.registerChatServer(registerMessage)

    server.start()

    # Server starts in background (in another thread) so keep waiting
    # if we don't wait here the main thread will end, which will end all the child threads, and thus the threads
    # from the server won't continue to work and stop the server

    server.wait_for_termination()
