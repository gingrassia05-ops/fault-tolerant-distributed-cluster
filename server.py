import os
import sys
from time import sleep
import time
import uuid
import socket
import threading
from multiprocessing import Lock
import json

#starting vars
def load_settings():
    settings_path = 'settings.json'
    try:
        with open(settings_path, 'r') as f:
            return json.load(f)
    except:
        print('[INIT ERROR]config file not found, server not ready yet, launch run.sh or update settings.json')
        sys.exit()




#Status vars
clients_connections_count = 0
active_http_clients = set()
http_clients_lock = threading.Lock()


def file_recv(node):
    #UPDATING CONFIG FILE
    #in case of a leader failure every node must know the latest situation
    #anybody could be elcted as leader
    data = node.recv(1024).decode()
    header, _ = data.split("<<END_HEAD>>")
    file_name, dimension = header.split(":")
    dimension = int(dimension)

    path = os.path.join(os.getcwd(), file_name)
    byte_counter = 0
    with open(path, "wb") as f:
        while byte_counter < dimension:
            remaining = dimension - byte_counter
            
            buffer = node.recv(min(4096, remaining))
            
            if not buffer:
                break
            f.write(buffer)
            byte_counter += len(buffer)
    #print(f"[LOG]File {file_name} saved in {path}")


#Handler SSE connection with actual client
#This is the core of service providing
#after the leader redirect to the server connection with client will be permanent until a server failure
#if leader fail connection still will be opened, another thread will restore the connection with a new leader
#if this node will be elected as leader all the connections will be closed
def send_chunk(conn, data):
    #HTTP Chunked Transfer Encoding to send data
    #data format: [hex lenght]\r\n[data]\r\
    chunk_size = hex(len(data))[2:].upper()
    packet = f"{chunk_size}\r\n{data}\r\n"
    conn.sendall(packet.encode('utf-8'))

#this function is the core of service providing
#as a new clients connects thi will be the handling thread fun
def handle_raw_client(conn, addr):
    #Breowser HTTP session handler
    #creating uniqe id for current session
    session_id = str(uuid.uuid4())[:8]
    
    try:
        # 1. getting request (es. GET / HTTP/1.1)
        request = conn.recv(1024).decode('utf-8')
        if not request:
            return

        # 2. Client registration
        with http_clients_lock:
            active_http_clients.add(session_id)
            # updating global var taht TCP thread will use as heartbeat
            global clients_connections_count
            clients_connections_count = len(active_http_clients)

        # 3. Sending HTTP Header for persistent streaming
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Transfer-Encoding: chunked\r\n" #Must have for a permanent connection
            "Connection: keep-alive\r\n"
            "Cache-Control: no-cache\r\n"
            "\r\n"
        )
        conn.sendall(headers.encode('utf-8'))

        # 4. Sending HTML base that will display datas
        with open("index.html", "r", encoding="utf-8") as f:
            index_content = f.read()
        send_chunk(conn, index_content)

        # 5. push loop
        print(f"[HTTP +] Client {addr} connected. Session: {session_id}")
        
        while True:
            with http_clients_lock:
                current_list = list(active_http_clients)
            
            # update() script calling in browser
            update_script = f"<script>update({json.dumps(current_list)});</script>"
            send_chunk(conn, update_script)
            
            # Heartbeat
            time.sleep(1)
    #connection error | closed | interrupted
    except (ConnectionResetError, BrokenPipeError, socket.error):
        print(f"[HTTP -] Client {addr} disconnected (Session: {session_id})")
    finally:
        # 6. Cleaning
        with http_clients_lock:
            if session_id in active_http_clients:
                active_http_clients.remove(session_id)
            clients_connections_count = len(active_http_clients)
        conn.close() #making sure to empty all the unecessary sessions

def run_node_http_server():
    try:
        #Main node Thread for HTTP socket
        http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        http_sock.bind((HOST, SERVICE_PORT))
        http_sock.listen(10)
        print(f"[INIT]Http server started successfully")
        
        while True:
            client_conn, addr = http_sock.accept()
            #basic multithread for each client permanent connection
            threading.Thread(target=handle_raw_client, args=(client_conn, addr), daemon=True).start()
    except Exception as e:
        print(f"[FATAL ERROR {e}]Http server start failure, restarting...")
        sleep(timeout)
        #if this process fails a fresh run is necessary
        os.execv(sys.executable, ['python3', './server.py'])


#To be leader connection_attempts numbers of fails must occour before
#the sleep time is proportional to the id number so there is nochance that 2 nodes tries simultaniusly
#one will for sure be elcted
#hope that the first attempt will go well :) 
def leader_connection():
    i = 0 #attemps counter
    while i < connection_attempts: #attemps counter
        #to make it as clean as possible every part of procedure will be fresh

        #node socket creating to comunicate with leader
        node = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        node.settimeout(timeout)
        try:
            #connecting to leader
            node.connect((HOST, LEADER_PORT))
            start_message = node.recv(1024).decode('utf-8')
            print(start_message)
            #sending id
            node.send(str(f"{self_id}:{SERVICE_PORT}").encode('utf-8'))

            #checking LeaderStatus and sending beat
            while True:
                try:
                    #config file recv procedure
                    file_recv(node)
                
                    #send active client connection counter as beat
                    node.send(str(clients_connections_count).encode('utf-8'))
                except Exception as e:
                    print(f"[ERROR]beating system fail: {e}")
                    break
            i = 0 #if the beat procedure fails the connection with leader can be restarted

        except Exception as e:
            print(f"[ERROR {e}]Leader not found or procedure error. Attemp {i+1}")
            i+=1
            sleep(self_id*timeout/2)
    #If 3 attempts fail server will become leader
    #if there is already leader this process will be repeted
    print(f"[Server -> LEADER]becoming leader procedure started")
    os.execv(sys.executable, ['python3', './leader.py'])
    

#COLD START
print(f"[INIT]Server started")
# loading settings
print(f"[INIT]Fetching settings")
settings = load_settings()

#Importing
self_id = settings["self_id"]
print(f"[INIT]Node number {self_id}")
HOST = settings["host"]
LEADER_PORT = settings["leader_port"]
#Loading custom service port
SERVICE_PORT = settings["service_port_base"] + self_id
file = settings["config_file_path"]
connection_attempts = settings["connection_attempts"]
timeout = settings["timeout"]
print(f"[INIT]Seeking leader on: {HOST}:{LEADER_PORT}")    
#setting up connection with leader
threading.Thread(target=leader_connection).start()

#Starting service providing
threading.Thread(target=run_node_http_server).start()

#InNode comand line
while True:
    prompt = input("")
    if prompt == "L":
        print(f"[Server -> LEADER]becoming leader procedure started")
        os.execv(sys.executable, ['python3', 'leader.py'])
