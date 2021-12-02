from concurrent import futures
import grpc
import uuid
import time
import sys
import helper_funcs
import datetime
from google.protobuf.timestamp_pb2 import Timestamp
import interfaces.globalmessage_pb2 as global_msg
import interfaces.nameservice_pb2 as ns_msg
import interfaces.nameservice_pb2_grpc as ns_rpc
import interfaces.databasefacade_pb2_grpc as rpc
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()


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
                'timestamp': datetime.datetime.now()
                }

        ref.set(data)
        return global_msg.Empty()


    def CreateUser(self, request: global_msg.User, context):
        #create refence to database document, ref will generate new document with a UID
        checkDatabaseRef = db.collection('Users').document(request.userName)
        doc = checkDatabaseRef.get()
        # # if username is already in database, then don't create user, else create user and upload data
        if doc.exists:
            print('Username is already in database')
        else:
            ref = db.collection('Users').document(request.userName)
            data = {'username': request.userName,
                    'displayName': request.displayName
                   }
            ref.set(data)
            print("User has been created")
        return global_msg.Empty()


    def CreateGroup(self, request: global_msg.Note, context):
        #create groups collection and store group under store with firebase generated UID, store group name under the uid
        checkGroupDatabaseRef = db.collection('Groups').document(request.group.name)
        doc = checkGroupDatabaseRef.get()
        #if name is already in database, then don't create a new group, else create group and uplaod data
        if doc.exists:
            print('Group name is already in database')
        else:
            #create reference to users-in-group collections
            ref = db.collection('Groups').document(request.group.name)
            ref.set([])
            print("Uploading group")
        #check if user is already stored in users-in-group collections
        checkUserDatabaseRef = db.collection('Groups').document(request.group.name).collection('users-in-group').document(request.user.userName)
        doc2 = checkUserDatabaseRef.get()
        if doc2.exists:
            print('User is already in this group')
        else:
            ref2 = db.collection('Groups').document(request.group.name).collection('users-in-group').document(request.user.userName)
            ref2.set([])
            print("Adding user to group")
        return global_msg.Empty()


    def FetchMessagesByGroup(self, request: global_msg.Group, context):
        print("Fetching group messages")
        docs = db.collection('Messages').where("groupName", "==", request.name).get()
        for doc in docs:
            print(doc.to_dict())
        print("Done fetching messages")
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

    database_server = ns_msg.RegisterServer()
    database_server.ipAddress = address_ns
    database_server.id = str(uuid.uuid4())
    database_server.port = port
    database_server.timestamp.GetCurrentTime()

    conn_ns.registerDatabase(database_server)

    server.start()
    server.wait_for_termination()