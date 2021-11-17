
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()


import interfaces.chatserver_pb2 as chat
import interfaces.chatserver_pb2_grpc as rpc



class Database:

    def createUser(self, request: chat.Note):
        #create refence to database document, ref will generate new document with a UID
        ref = db.collection('Users').document()
        userUID = ref.id
        data = {'username': request.name,
                'uid': userUID}
        ref.set(data)

    def createGroup(self, request: chat.Note):
        #create groups collection and store group under store with firebase generated UID, store group name under the uid
        ref = db.collection('Groups').document()
        groupID = ref.id
        data = {'groupName': request.group,
                'id': groupID}
        ref.set(data)

    def postMessage(self, request: chat.Note):
        print("Uploading messages")
        #create refence to database document, ref will generate new document with a UID
        ref = db.collection('Messages').document()
        messageID = ref.id
        data = {'messageID': messageID,
                'username': request.name,
                'message': request.message,
                'groupName': request.group,
                'timestamp': 0}
        ref.set(data)

    #function to query messages based on the group name
    def fetchMessagesForGroup(self, request: chat.Note):
        print('Fetching data')
        docs = db.collection('Messages').where("groupName", "==", request.group).get()
        for doc in docs:
            print(doc.to_dict())

    #function to fetch all messages stored and return each messages data
    def fetchMessages(self, request: chat.Note):
        docs = db.collection('Messages').get()
        for doc in docs:
            messageID = doc.id
            self.fetchMessage(messageID)

    #function to fetch one message by its messageID
    #only use in the fetchAlleMessages function
    def fetchMessage(self, messageID):
        doc = db.collection('Messages').document(messageID).get()
        if doc.exists:
            print(doc.to_dict())

    def fetchGroups(self):
        docs = db.collection('Groups').get()
        for doc in docs:
            print(doc.to_dict())

    def fetchUsers(self):
        docs = db.collection('Users').get()
        for doc in docs:
            userUID = doc.id
            self.fetchUser(userUID)

    def fetchUser(self, userUID):
        doc = db.collection('Users').document(userUID).get()
        if doc.exists:
            print(doc.to_dict())




    # #Just for testing framework for some of the functions above

    #create user

    ref = db.collection('Users').document()
    userUID = ref.id
    data1 = {'username': 'Bob',
             'uid': userUID}
    ref.set(data1)

    # post message

    ref1 = db.collection('Messages').document()
    messageID = ref1.id
    data = {'messageID': messageID,
            'username': 'Bob',
            'message': 'Hello',
            'groupName': 'New Group',
            'timestamp': 0}
    ref1.set(data)

    #create group

    ref2 = db.collection('Groups').document()
    groupID = ref2.id
    data = {'groupName': 'New Group',
            'id': groupID}
    ref2.set(data)

    #query messages based on group name

    docs = db.collection('Messages').where("groupName", "==", 'New Group').get()
    for doc in docs:
        print(doc.to_dict())

    #fetch user by UID

    doc = db.collection('Users').document('MnCjk8w5LihNjhaTUYEF').get()
    if doc.exists:
        print(doc.to_dict())


