import os
import select
import socket
from threading import Thread
import networking

zeroTierIP = None
PORT_NUMBER = 45154

# Obtain script path and script name, it will be useful to manage filepaths
scriptPath, scriptName = os.path.split((os.path.abspath(__file__).replace("\\", "/")))
scriptPath += "/"

class Server:
    """
    Multithread server class that will manage incoming connections.
    For each incoming connection it will create a thread.
    This thread will manage the request and terminate.
    The server runs until the property __stop is equals to False.
    The port on which the server will listen is choosen among available ports.
    """

    def __init__(self, port, maxClients=5):
        """
        Initialize server.
        :param port: port number on which the server will be reachable
        :param maxClients: maximum number of incoming connections.
        :return: void
        """

        # Initialize the server with a host and port to listen to.
        # Provide a list of functions that will be used when receiving specific data
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", port))

        self.host = networking.getMyIP()
        self.port = port

        self.sock.listen(maxClients)
        self.sockThreads = []
        self.counter = 0  # Will be used to give a number to each thread, can be improved (re-assigning free number)
        self.__stop = False

        """ Accept an incoming connection.
        Start a new SocketServerThread that will handle the communication. """
        print('Starting socket server (host {}, port {})'.format(self.host, self.port))

        while not self.__stop:
            try:
                self.sock.settimeout(1)
                try:
                    clientSock, clientAddr = self.sock.accept()
                except socket.timeout:
                    clientSock = None

                if clientSock:
                    clientThr = SocketServerThread(clientSock, clientAddr, self.counter)
                    self.counter += 1
                    self.sockThreads.append(clientThr)
                    clientThr.daemon = True
                    clientThr.start()
            except KeyboardInterrupt:
                self.stopServer()

        self.closeServer()

    def closeServer(self):
        """ Close the client socket threads and server socket if they exists. """
        print('Closing server socket (host {}, port {})'.format(self.host, self.port))

        for thr in self.sockThreads:
            thr.stop()

        if self.sock:
            self.sock.close()

        networking.leaveNetwork()

        exit()

    def stopServer(self):
        """This function will be called in order to stop the server (example using the X on the GUI or a signal)"""
        self.__stop = True


class SocketServerThread(Thread):
    def __init__(self, clientSock, clientAddr, number):
        """ Initialize the Thread with a client socket and address """
        Thread.__init__(self)
        self.clientSock = clientSock
        self.clientAddr = clientAddr
        self.number = number
        self.__stop = False

    def run(self):

        # print("[Thr {}] SocketServerThread starting with client {}".format(self.number, self.clientAddr))

        while not self.__stop:
            if self.clientSock:
                # Check if the client is still connected and if data is available:
                try:
                    rdyRead, __, __ = select.select([self.clientSock, ], [self.clientSock, ], [], 5)
                except select.error:
                    print('[Thr {}] Select() failed on socket with {}'.format(self.number, self.clientAddr))
                    self.stop()
                    return

                if len(rdyRead) > 0:
                    readData = networking.myRecv(self.clientSock)

                    # Check if socket has been closed
                    if len(readData) == 0:
                        print('[Thr {}] {} closed the socket.'.format(self.number, self.clientAddr))
                        self.stop()
                    else:
                        # Strip newlines just for output clarity
                        request = readData.rstrip()
                        self.manageRequest(request)
            else:
                print("[Thr {}] No client is connected, SocketServer can't receive data".format(self.number))
                self.stop()
        self.close()

    def stop(self):
        self.__stop = True

    def close(self):
        """ Close connection with the client socket. """
        if self.clientSock:
            # print('[Thr {}] Closing connection with {}'.format(self.number, self.clientAddr))
            self.clientSock.close()

    def manageRequest(self, request):
        """
        Manage different request.
        :param request: incoming request
        :return: void
        """

        action = request.split()[0]
        
        if action == "GET":
            print("Received: " + request)
            try:
                filename = request.split()[1]
                filepath = scriptPath + "files/" + filename
                f = open(filepath, "r")
                f.close()
                answer = "OK - SENDING FILE"
                networking.mySend(self.clientSock, answer)
                networking.sendFile(self.clientSock, filepath)
            except (FileNotFoundError, IndexError):
                answer = "ERROR - FILE NOT FOUND"
                networking.mySend(self.clientSock, answer)

        elif action == "INFO":
            answer = str((zeroTierIP, PORT_NUMBER))
            networking.mySend(self.clientSock, answer)

        elif action == "BYE":
            answer = "OK - BYE PEER"
            networking.mySend(self.clientSock, answer)
            self.stop()

        else:
            answer = "ERROR - UNEXPECTED REQUEST"
            networking.mySend(self.clientSock, answer)


if __name__ == '__main__':

    # joins ZeroTier network
    zeroTierIP = networking.joinNetwork()
    print("Server's ZeroTier IP: ", zeroTierIP)

    # run the server until CTRL+C interrupt
    server = Server(PORT_NUMBER)
