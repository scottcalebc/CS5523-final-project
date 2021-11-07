import threading
from tkinter import *
from tkinter import simpledialog

import grpc
import sys
import helper_funcs

import interfaces.globalmessage_pb2 as global_msg

import interfaces.chatserver_pb2 as chat
import interfaces.chatserver_pb2_grpc as rpc

import interfaces.nameservice_pb2 as chat_ns
import interfaces.nameservice_pb2_grpc as rpc_ns


class Client:

    def __init__(self, u: str, g: str, chatServer, window):
        # the frame to put ui components on
        self.window = window
        self.username = u
        self.group = g
        # create a gRPC channel + stub
        channel = grpc.insecure_channel(chatServer.ipAddress + ':' + str(chatServer.port))
        self.conn = rpc.ChatServerStub(channel)
        # create new listening thread for when new message streams come in
        threading.Thread(target=self.__listen_for_messages, daemon=True).start()
        self.__setup_ui()
        self.window.mainloop()

    def __listen_for_messages(self):
        """
        This method will be ran in a separate thread as the main/ui thread, because the for-in call is blocking
        when waiting for new messages
        """
        g = chat.Group()
        g.name = self.group
        for note in self.conn.ChatStream(g):  # this line will wait for new messages from the server!
            print("R[{}] {}".format(note.name, note.message))  # debugging statement
            self.chat_list.insert(END, "[{}] {}\n".format(note.name, note.message))  # add the message to the UI

    def send_message(self, event):
        """
        This method is called when user enters something into the textbox
        """
        message = self.entry_message.get()  # retrieve message from the UI
        if message is not "":
            n = chat.Note()  # create protobug message (called Note)
            n.name = self.username  # set the username
            n.message = message  # set the actual message of the note
            n.group = self.group
            print("S[{}] {}".format(n.name, n.message))  # debugging statement
            self.conn.SendNote(n)  # send the Note to the server

    def __setup_ui(self):
        self.chat_list = Text()
        self.chat_list.pack(side=TOP)
        self.lbl_username = Label(self.window, text=self.username)
        self.lbl_username.pack(side=LEFT)
        self.entry_message = Entry(self.window, bd=5)
        self.entry_message.bind('<Return>', self.send_message)
        self.entry_message.focus()
        self.entry_message.pack(side=BOTTOM)


if __name__ == '__main__':
    root = Tk()  # I just used a very simple Tk window for the chat UI, this can be replaced by anything
    frame = Frame(root, width=300, height=300)
    frame.pack()
    root.withdraw()
    username = None
    while username is None:
        # retrieve a username so we can distinguish all the different clients
        username = simpledialog.askstring("Username", "What's your username?", parent=root)
        group = simpledialog.askstring("Group", "What group do you want to join?", parent=root)
    root.deiconify()  # don't remember why this was needed anymore...

    # first need to get server information
    port_ns = 3535
    address_ns = 'localhost'
    ns = grpc.insecure_channel(address_ns + ':' + str(port_ns))
    conn_ns = rpc_ns.NameServerStub(ns)



    groupMsg = global_msg.Group()
    groupMsg.name = group
    chatServer = conn_ns.getChannel(groupMsg)

    if chatServer.status != 1:
        print("Could not find server disconnecting")
        sys.exit(1)      

    c = Client(username, group, chatServer, frame)  