import threading

import grpc
import uuid
import sys
import time
import datetime
import random
import argparse

from google.protobuf.timestamp_pb2 import Timestamp

import interfaces.globalmessage_pb2 as global_msg

import interfaces.chatserver_pb2_grpc as rpc

import interfaces.nameservice_pb2_grpc as rpc_ns




class Client:

    def __init__(self, file_text, chatServer):
        with open(file_text, "r") as f:
            self.text = f.read().split()
        # create a gRPC channel + stub
        self.id = 0
        channel = grpc.insecure_channel(chatServer.ipAddress + ':' + str(chatServer.port))
        self.conn = rpc.ChatServerStub(channel)
        # create new listening thread for when new message streams come in

    def send_messages(self):
    
        id = uuid.uuid4()
        name = f"test_client"
        while True:
            word = random.choice(self.text)
            print(f"Sending message with word: {word}")
            n = global_msg.Note()
            n.user.userName = str(id)  # set the username
            n.user.displayName = name
            n.message = word  # set the actual message of the note
            n.group.name = "test"
            now = datetime.datetime.now()
            # ts = Timestamp()
            # ts.FromDatetime(now)
            n.timestamp.FromDatetime(now)
            self.conn.SendNote(n)
            time.sleep(1)




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Test program to run several clients simultaneously against chat server")
    parser.add_argument("-f", "--file", action="store")
    args = parser.parse_args()
    print(args)


    # first need to get server information
    port_ns = 3535
    address_ns = 'localhost'
    ns = grpc.insecure_channel(address_ns + ':' + str(port_ns))
    conn_ns = rpc_ns.NameServerStub(ns)



    groupMsg = global_msg.Group()
    groupMsg.name = "test"
    chatServer = conn_ns.getChannel(groupMsg)

    if chatServer.status != 1:
        print("Could not find server disconnecting")
        sys.exit(1)      

    c = Client( args.file, chatServer )  
    c.send_messages()