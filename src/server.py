from concurrent import futures

import grpc
import time

import helper_funcs

import interfaces.globalmessage_pb2 as global_msg

import interfaces.chatserver_pb2_grpc as rpc

import interfaces.nameservice_pb2 as ns_msg
import interfaces.nameservice_pb2_grpc as ns_rpc


# test comment for local change



class ChatServer(rpc.ChatServerServicer):  # inheriting here from the protobuf rpc file which is generated

    def __init__(self):
        # List with all the chat history
        self.chats = {}
        self.clients = {}

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
        print(f"Request for group {request.name}")
        if self.chats.get(request.name, None) == None:
            self.chats[request.name] = []

        # if self.clients.get(request.user.userName, None) == None:
        #     group_index = 0 if len(self.chats[request.group.name]) < 1 else len(self.chats[request.group.name]) - 1
        #     self.clients[request.user.userName] = {request.group.name : group_index}

        lastindex = 0 if len(self.chats[request.name]) == 0 else len(self.chats[request.name])

        # For every client a infinite loop starts (in gRPC's own managed thread)
        while True:
            # Check if there are any new messages
            while len(self.chats[request.name]) > lastindex:
                n = self.chats[request.name][lastindex]
                lastindex += 1
                yield n

    def SendNote(self, request: global_msg.Note, context):
        """
        This method is called when a clients sends a Note to the server.

        :param request:
        :param context:
        :return:
        """
        # this is only for the server console
        print(request)
        print("[{}] {} in group {}".format(request.user.displayName, request.message, request.group.name))
        # Add it to the chat history
        if self.chats.get(request.group.name, None) == None:
            self.chats[request.group.name] = []

        # if self.clients.get(request.user.userName, None) == None:
        #     group_index = len(self.chats[request.user.userName])
        #     self.clients[request.user.userName] = {request.group.name : group_index }
        # else:
        #     self.clients[request.user.userName][request.group.name] = len(self.chats[request.group.name])

        self.chats[request.group.name].append(request)
        return global_msg.Empty()  # something needs to be returned required by protobuf language, we just return empty msg


if __name__ == '__main__':
    port = 11912  # a random port for the server to run on
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
    registerMessage.id = "1234"
    registerMessage.port = port
    print(registerMessage.ipAddress)

    g = global_msg.Group()
    g.name = "all"
    conn_ns.getChannel(g)

    conn_ns.registerChatServer(registerMessage)


    server.start()

    # Server starts in background (in another thread) so keep waiting
    # if we don't wait here the main thread will end, which will end all the child threads, and thus the threads
    # from the server won't continue to work and stop the server

    server.wait_for_termination()
