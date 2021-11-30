# main and thread packages
import os
import signal
import threading

# gui packages
import tkinter
from tkinter import simpledialog
from tkinter import messagebox


# utility packages
import sys
import time
import datetime
import helper_funcs

# rpc and protobuf functions
import grpc

from google.protobuf.timestamp_pb2 import Timestamp
import interfaces.globalmessage_pb2 as global_msg

import interfaces.chatserver_pb2 as chat
import interfaces.chatserver_pb2_grpc as rpc

import interfaces.nameservice_pb2 as chat_ns
import interfaces.nameservice_pb2_grpc as rpc_ns


# READ ONLY DEFINES
MAX_TIMEOUT=1.0 #500
MAX_RETRIES=5

# Main excit exception for signal handler to pass to main thread
class MainExit(Exception):
    pass

# method to allow threads to signal main thread for exit
def signal_handler(signal, frame):
    raise MainExit()

class Client:

    def __init__(self, u: str, g: str, window, root):

        # main setup first before setting up rpc
        self.username = u
        self.group = g

        # the frame to put ui components on
        self.root = root
        self.window = window 
        self.__setup_ui()

        # get chat name server first
        self.chatServer = self.__get_ChatServer()
        if self.chatServer == None:
            print("Chat Server could not be found")
            raise MainExit


        # connection thread event managers
        self.connected_event = threading.Event()
        self.disconneted_event = threading.Event()

        # connection lock
        self.connection_lock = threading.Lock()
        self.channel = grpc.insecure_channel(self.chatServer.ipAddress + ':' + str(self.chatServer.port))
        self.channel.subscribe(self.__channel_connection_monitor)
        self.conn = rpc.ChatServerStub(self.channel)
        self.retry = 0
        self.total_retries = 0

        # messaging lock to prevent queueing / sending of the same message numerous times by
        #   repeated presses of the enter key
        self.message_lock = threading.Lock()

        # clear events to prevent processing before validating connection status
        self.disconneted_event.clear()
        self.connected_event.clear()

    
        # create new listening thread for when new message streams come in
        threading.Thread(name="Message Listener",target=self.__listen_for_messages, daemon=True).start()
        threading.Thread(name="History Daemon",target=self.__test_GetHistory, daemon=True).start()
        threading.Thread(name="Connection Handler", target=self.__connectionMgr, daemon=True).start()

        
        # if receiving exception from signal will be handled outsie of Client class
        self.window.mainloop()


    def __connection_request(self, func, parameter, name=None):
        self.connected_event.wait(timeout=MAX_TIMEOUT)
        if self.connected_event.is_set():
            with self.connection_lock:
                try:

                    retValue = func(parameter)

                    # validate calling code should work on return value object
                    # this will ensure multithreaded objects like stream iterators are accessed before
                    # passing back to user code and will throw exceptions here
                    if retValue.code():
                        self.total_retries = 0
                        return retValue
                    else:
                        return None
                    

                except grpc.RpcError as e:
                    # collect status code from rpc server
                    status_code = e.code()
                    print(f"Handling Exception during rpc call {name} for {status_code}")
                    

                    if (status_code == grpc.StatusCode.UNAVAILABLE or 
                        status_code == grpc.StatusCode.DEADLINE_EXCEEDED or
                        status_code == grpc.StatusCode.UNKNOWN):
                        if self.retry > MAX_RETRIES:
                            self.connected_event.clear()
                            self.disconneted_event.set()
                        else:
                            self.retry = self.retry + 1
                    elif (status_code == grpc.StatusCode.INTERNAL):
                        self.chat_write("Internal Error from rpc connection, restart application")
                        time.sleep(5)
                        os.kill(os.getpid(), signal.SIGUSR1)
                    else:
                        print(f"Recevied unhandled connection error {e}")
                        print(f"Received code from error {status_code}")
                        raise e
        # should be hit
        return None

    def __get_ChatServer(self):
        port_ns = 3535
        address_ns = 'localhost'
        ns = grpc.insecure_channel(address_ns + ':' + str(port_ns))
        conn_ns = rpc_ns.NameServerStub(ns)

        groupMsg = global_msg.Group()
        groupMsg.name = self.group    
        retry = 0
        while retry < MAX_RETRIES:
            try:
                print("Attempting to connect to name server")
                chatServer = conn_ns.getChannel(groupMsg)
                print(f"Received from Name Server: {chatServer}")
                if chatServer.status == -1:
                    raise MainExit

                return chatServer
            except grpc.RpcError as e:
                status_code = e.code()

                if (status_code == grpc.StatusCode.UNAVAILABLE or 
                        status_code == grpc.StatusCode.DEADLINE_EXCEEDED or
                        status_code == grpc.StatusCode.UNKNOWN):

                        retry = retry + 1
                if (status_code == grpc.StatusCode.INTERNAL):
                        self.chat_write("Internal Error from rpc connection, restart application")
                        time.sleep(5)
                        os.kill(os.getpid(), signal.SIGUSR1)

        return None

    def __channel_connection_monitor(self, chan_conn):
        if (chan_conn == grpc.ChannelConnectivity.IDLE or
            chan_conn == grpc.ChannelConnectivity.READY):
            self.disconneted_event.clear()
            self.connected_event.set()
            self.total_retries = 0
    
        if (chan_conn == grpc.ChannelConnectivity.TRANSIENT_FAILURE or
                chan_conn == grpc.ChannelConnectivity.SHUTDOWN):
            self.connected_event.clear()
            self.disconneted_event.set()
            

    def __connectionMgr(self):
        while True:
            self.disconneted_event.wait(timeout=MAX_TIMEOUT)
            if self.disconneted_event.is_set():
                self.__get_ChatServer()

                print(f"Total retries = {self.total_retries}")
                if self.total_retries > MAX_RETRIES:
                    os.kill(os.getpid(), signal.SIGUSR1)

                with self.connection_lock:
                    self.chat_write("Disconneted from Server. Attempting to reconnect...\n")
                    self.channel = grpc.insecure_channel(self.chatServer.ipAddress + ':' + str(self.chatServer.port))
                    self.conn = rpc.ChatServerStub(self.channel)
                    self.retry = 0
                    self.total_retries = self.total_retries + 1
                    print(f"Incrementing connection retries in a row {self.total_retries}")
                    self.disconneted_event.clear()
                    self.connected_event.set()


    def __test_GetHistory(self):
        
        hist = global_msg.GroupHistory()
        hist.user.userName = self.username
        hist.user.displayName = self.username
        hist.group.name = self.group
        print("Testing GetHistory")
        # resp = self.conn.GetHistory(hist)
        resp = self.__connection_request(self.conn.GetHistory, hist, "GetHistory")
        if resp != None:
            print(resp.details())

    
    
    def __listen_for_messages(self):
        """
        This method will be ran in a separate thread as the main/ui thread, because the for-in call is blocking
        when waiting for new messages
        """
        g = global_msg.Group()
        g.name = self.group

        while True:
            # self.connected_event.wait(timeout=MAX_TIMEOUT)
            if self.connected_event.is_set():
                # self.conn.ChatStream(g)
                try:
                    chat_iter = self.__connection_request(self.conn.ChatStream, g, "ChatStream")
                            # self.chat_list.insert(END, "[{} @ {}] {}\n".format(note.user.displayName, date, note.message))  # add the message to the UI
                    # self.chat_list.see(END)
                except grpc.RpcError:
                    chat_iter = iter(())
                if chat_iter == None:
                    continue
                for note in chat_iter:  # this line will wait for new messages from the server!
                        print(note)
                        print("R[{}] {}".format(note.user.displayName, note.message))  # debugging statement
                        date = note.timestamp.ToDatetime()
                        self.chat_write("[{} @ {}] {}\n".format(note.user.displayName, date, note.message))

    def chat_write(self, msg):
        self.chat_list.configure(state='normal')
        self.chat_list.insert(tkinter.END, msg)
        self.chat_list.see(tkinter.END)
        self.chat_list.configure(state='disabled')

    def send_message(self, event):
        """
        This method is called when user enters something into the textbox
        """
        with self.message_lock:
            message = self.entry_message.get()  # retrieve message from the UI
            self.entry_message.configure(state="disabled")
            value = None # place holder to validate response from server when deleteing UI element text
            if message != "": # self.connected_event.is_set() and getattr(self.conn, "SendNote", None) != None:
                n = global_msg.Note()  # create protobug message (called Note)
                print(n)
                n.user.userName = self.username  # set the username
                n.user.displayName = self.username
                n.message = message  # set the actual message of the note
                n.group.name = self.group
                now = datetime.datetime.now()
                # ts = Timestamp()
                # ts.FromDatetime(now)
                n.timestamp.FromDatetime(now)
                print("S[{} @ {}] {}".format(n.user.displayName, now, n.message))  # debugging statement

                # self.conn.SendNote(n)  # send the Note to the server
                value = None
                # while value == None and self.connected_event.is_set():
                while value == None and self.connected_event.is_set():
                    try:
                        value = self.__conn_request("SendNote", n)
                    except grpc.RpcError as e:
                        status_code = e.code()

                        print(f"Received unhandled rpc error from connection request: {status_code}")
                        break
            
            self.entry_message.configure(state="normal")
            if value != None:
                self.entry_message.delete(0, tkinter.END)

    def __setup_ui(self):
        self.chat_list = tkinter.Text(self.window, highlightthickness=0, state='disabled')
        self.chat_list.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        
        # frame to hold three widgets side-by-side
        frame = tkinter.Frame(self.window)
        frame.pack(side=tkinter.BOTTOM)
        self.lbl_username = tkinter.Label(frame, text=self.username, highlightthickness=0)
        self.lbl_username.pack(side=tkinter.LEFT, padx=5)
        self.entry_message = tkinter.Entry(frame, bd=5)
        self.entry_message.bind('<Return>', self.__send_message_wrapper)
        self.entry_message.focus()
        self.entry_message.pack(side=tkinter.LEFT, padx=5)

        # I added exit button instead of clicking ctrl+c to exit client##
        self.exit_button = tkinter.Button(frame, text="Quit", command=self.root.destroy)
        self.exit_button.pack(side=tkinter.LEFT, padx=5)

        
####################################connection errors#######



############################################################

def getAccountAndGroup(root):
    confirm = True
    username = None
    group = None

    while confirm:
        username = simpledialog.askstring("Username", "What's your username?", parent=root)
        if username == None:
            confirm = messagebox.askquestion(title="cdsRpc", message="Do you want to quit?")

            if confirm == "yes":
                sys.exit(1)
            else:
                confirm = True
        else:
            break
                
    while confirm:
        group = simpledialog.askstring("Group", "What group do you want to join?", parent=root)
        if group == None:
            confirm = messagebox.askquestion(title="cdsRpc", message="Do you want to quit?")
            if confirm == "yes":
                sys.exit(1)
            else:
                confirm = True
        else:
            break

    
    return username, group


if __name__ == '__main__':
    print(f"open is assigned to {open}")
    root = tkinter.Tk()  # I just used a very simple Tk window for the chat UI, this can be replaced by anything
    frame = tkinter.Frame(root, width=300, height=300)
    frame.pack()
    root.withdraw()
    username = None
    
    username, group = getAccountAndGroup(root)
    # Remove user username/group loop allows user to leave application early
    # retrieve a username so we can distinguish all the different clients
    # username = simpledialog.askstring("Username", "What's your username?", parent=root)
    # if username == None:
    #     print("Exiting...")
    #     os.exit(1)
    
    # group = simpledialog.askstring("Group", "What group do you want to join?", parent=root)
    # if group == None:
    #     print("Exiting...")
    #     os.exit(1)
    
    root.deiconify()  # don't remember why this was needed anymore...

    # This is to catch the MainExit exception thrown by threads, will block if any threads
    #       are non-daemon 
    try:
        c = Client(username, group, frame, root)  
    except MainExit:
        pass