import networking
import sys
import socket
import math
import time
import os
from threading import Thread

serverZTaddr = None

# Obtain script path and script name, it will be useful to manage filepaths
scriptPath, scriptName = os.path.split((os.path.abspath(__file__).replace("\\", "/")))
scriptPath += "/"

def getServerZTAddr(serverAddr):
    """
    Get server ZT address.
    :serverAddr: (IP, port) tuple representing server real address
    :return: void
    """

    global serverZTAddr

    s = networking.createConnection(serverAddr)
    if s is None:
        return

    try:
        # send request message and wait for the answer, then close the socket
        message = "INFO"
        networking.mySend(s, message)
        answer = networking.myRecv(s)
        networking.closeConnection(s)
    except (socket.timeout, RuntimeError):
        networking.closeConnection(s)
        return False

    serverZTAddr = eval(answer)


def getFile(filename):
    """
    Ask central server for the file and then retrieve it.
    Record and print download time.
    :filename: name of the file
    :return: void
    """

    start = time.time()

    print("File {} reception starts".format(filename))

    s = networking.createConnection(serverZTAddr)
    if s is None:
        return None

    try:
        message = "GET {}".format(filename)
        networking.mySend(s, message)
        answer = networking.myRecv(s)

        if answer.split()[0] == "OK":
            filepath = scriptPath + "recv/" + filename
            networking.recvFile(s, filepath)

        networking.closeConnection(s)
    except (socket.timeout, RuntimeError):
        networking.closeConnection(s)
        return None

    end = time.time()

    print("File {} received in {} seconds".format(filename, math.floor(end-start)))



if __name__ == '__main__':
    """
    To run the script use:
    python3 client.py <serverIP> <serverPort> <filename1> ... <filenameN>
    """

    # acquire server addressù
    serverIP = sys.argv[1]
    serverPort = sys.argv[2]

    # acquire file list
    filelist = list(sys.argv[3:])

    # join ZeroTeri network
    zeroTierIP = networking.joinNetwork()

    # find server ZT address
    getServerZTAddr((serverIP, serverPort))
    threads = list()

    # download all the file
    for filename in filelist:

        t = Thread(target=getFile, args=(filename,))
        t.daemon = True
        threads.append(t)
        t.start()

    # wait for all downloads termination
    for t in threads:
        t.join()

    networking.leaveNetwork()

        
