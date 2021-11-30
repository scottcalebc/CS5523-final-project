from concurrent import futures

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

import grpc
import time

import helper_funcs

import interfaces.globalmessage_pb2 as global_msg

import interfaces.nameservice_pb2 as ns_msg
import interfaces.nameservice_pb2_grpc as ns_rpc

import interfaces.databasefacade_pb2_grpc as rpc


class DatabaseServer(rpc.DatabaseServerServicer):

    def UploadMessage(self, request: global_msg.Note, context):
        print("Uploading messages")
        #create refence to database document, ref will generate new document with a UID
        ref = db.collection('Messages').document()
        print(request)
        messageID = ref.id
        data = {'messageID': messageID,
                'username': request.user.displayName,
                'message': request.message,
                'groupName': request.group.name,
                'timestamp': request.timestamp}
        ref.set(data)
        return global_msg.Empty()

    def CreateUser(self, request: global_msg.Note, context):
        print("Creating user")
        #create refence to database document, ref will generate new document with a UID
        ref = db.collection('Users').document()
        print(request)
        userUID = ref.id
        data = {'username': request.user.username,
                'displayName': request.user.displayName,
                'uid': userUID}
        ref.set(data)
        return global_msg.Empty()

    def CreateGroup(self, request: global_msg.Group, context):
        print("Uploading group")
        #create groups collection and store group under store with firebase generated UID, store group name under the uid
        ref = db.collection('Groups').document()
        print(request)
        groupID = ref.id
        data = {'groupName': request.group.name,
                'id': groupID}
        ref.set(data)
        return global_msg.Empty()

    def FetchMessagesByGroup(self, request: global_msg.Group, context):
        print("Fetching group messages")
        docs = db.collection('Messages').where("groupName", "==", request.group.name).get()
        for doc in docs:
            print(doc.to_dict())
        return global_msg.Note()

if __name__ == '__main__':
    port = 11864  # a random port for the server to run on
    # the workers is like the amount of threads that can be opened at the same time, when there are 10 clients connected
    # then no more clients able to connect to the server.
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))  # create a gRPC server
    rpc.add_DatabaseServerServicer_to_server(DatabaseServer(), server)  # register the server to gRPC
    # gRPC basically manages all the threading and server responding logic, which is perfect!
    print('Starting Database. Listening...')
    server.add_insecure_port('127.0.0.1:' + str(port))

    # first need to get server information
    port_ns = 3535
    address_ns = '127.0.0.1'
    ns = grpc.insecure_channel(address_ns + ":" + str(port_ns))
    conn_ns = ns_rpc.NameServerStub(ns)

    server.start()
    server.wait_for_termination()