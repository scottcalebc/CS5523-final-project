
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

import interfaces.globalmessage_pb2 as global_msg

import interfaces.nameservice_pb2 as ns_msg
import interfaces.nameservice_pb2_grpc as ns_rpc

import interfaces.databasefacade_pb2_grpc as rpc


class Database(rpc.DatabaseServerServicer):

    def UploadMessage(self, request: global_msg.Note, context):
        #create refence to database document, ref will generate new document with a UID
        ref = db.collection('Messages').document()
        messageID = ref.id
        data = {'messageID': messageID,
                'username': request.name,
                'message': request.message,
                'groupName': request.group }
        ref.set(data)
        print("Uploading messages")
        return global_msg.Empty()

    def CreateUser(self, request: global_msg.Note, context):
        #create refence to database document, ref will generate new document with a UID
        ref = db.collection('Users').document()
        userUID = ref.id
        data = {'username': request.name,
                'uid': userUID}
        ref.set(data)
        return global_msg.Empty()

    def CreateGroup(self, request: global_msg.Group, context):
        #create groups collection and store group under store with firebase generated UID, store group name under the uid
        ref = db.collection('Groups').document()
        groupID = ref.id
        data = {'groupName': request.name,
                'id': groupID}
        ref.set(data)
        return global_msg.Empty()

    def FetchMessagesByGroup(self, request: global_msg.Group, context):
        docs = db.collection('Messages').where("groupName", "==", request.name).get()
        for doc in docs:
            print(doc.to_dict())
        return global_msg.Note()

if __name__ == '__main__':
    port = 11864  # a random port for the server to run on
    # the workers is like the amount of threads that can be opened at the same time, when there are 10 clients connected
    # then no more clients able to connect to the server.
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))  # create a gRPC server
    rpc.add_DatabaseServerServicer_to_server(Database(), server)  # register the server to gRPC
    # gRPC basically manages all the threading and server responding logic, which is perfect!
    print('Starting server. Listening...')
    # server.add_insecure_port('127.0.0.1:' + str(port))