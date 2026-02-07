import os
import sys
from time import sleep
import stat
import socket
import threading
from multiprocessing import Lock
import json



def load_settings():
    settings_path = 'settings.json'
    
    # 1. checking settings file
    if not os.path.exists(settings_path):
        print(f"[FATAL ERROR] Leader settings file '{settings_path}' not found.")
        sys.exit(1)
    
    try:
        with open(settings_path, 'r') as f:
            data = json.load(f)
            
        # 2. checking keys
        required_keys = ["host", "leader_port", "service_port", "config_file_path", "self_id"]
        for key in required_keys:
            if key not in data:
                print(f"[FATAL ERROR] Missing required key '{key}' in {settings_path}")
                sys.exit(1)
                
        return data
        
    except json.JSONDecodeError:
        print(f"[FATAL ERROR] '{settings_path}' is not a valid JSON file.")
        sys.exit(1)






#config file sending function to node(conn)
def send_file(conn):
    file_name = os.path.basename(file)
    dimension = os.path.getsize(file)
    header = f"{file_name}:{dimension}<<END_HEAD>>"
    conn.sendall(header.encode())
    with file_lock:
        with open(file_name, "rb") as f:
            while True:
                buffer = f.read(4096)
                if not buffer:
                    break
                conn.sendall(buffer)

#This long function is the core of the fault-tolerance infrastructure
#As a new connection to the leader port and verification of the id, it must be handled as a new node, a member of the cluster
#Anytime from now a problem may occour,server fail, leader fail, connection fail, but the cluster must be human-free
#If a problem happens to be, service must be provided, good
#this function makes it possible
 
def new_server_handle(conn, addr):
    #new node is trying to connect, a new thread is created 
    global connection
    conn.settimeout(10)
    print(f"[LOG] node connected: {addr}")
    welcome_message = 'CONNECTION CONFIRM\nWelcome!'
    conn.send(welcome_message.encode('utf-8'))

    #id assign
    load = conn.recv(1024).decode('utf-8')
    id, service_port = load.split(":")

    #updating config file with new node info, or creating a new section
    with file_lock:
        with open(file, "r") as f:
            config = json.load(f)
        if id not in config["nodes"]:
            config["nodes"][f"node_{id}"] = {}
        config["nodes"][f"node_{id}"] = {"ip": addr[0],"port": addr[1],"status": "ONLINE","load": 0,"id":id,"service port":service_port}
        config["cluster_info"]["node number"] = len(config['nodes'])
        with open(file, "w") as f:
            json.dump(config, f, indent=4,sort_keys=True)
    
    #sending updated config file as a ceantral heartbeat to confirm that leader is online
    try:
        while True:
            sleep(5)
            #send file procedure
            send_file(conn)

            #receiving beat with the update of active clients connections
            clients = conn.recv(1024).decode('utf-8')
            if clients != "":
                with file_lock:
                    if os.path.exists(file) and os.path.getsize(file) > 0:
                        with open(file, "r") as f:
                            config = json.load(f)
                    #update load entry       
                    config["nodes"][f"node_{id}"]["load"] = int(clients)

                    with open(file, "w") as f:
                        json.dump(config, f, indent=4, sort_keys=True)

    #handling node not responding
    #after a comm fail the connection will be closed
    #status node must be setted as offline
    #if the node will restart a new thread will handle it again        
    except Exception as e:
        #updating node status to offline
        with file_lock:
            with open(file, "r") as f:
                config = json.load(f)
            config["nodes"][f"node_{id}"]["status"] = 'OFFLINE'
            with open(file, "w") as f:
                json.dump(config, f, indent=4,sort_keys=True)
        print(f"[LOG][CONNECTION ERROR {e}] node_{id} is not responding: connection closed")
    with connection_lock:
            x= connection
            x = x -1 
            connection = x

#returns ip and port for service of the least loaded node
def get_best_node():
    #Finds the online node with the minimum client load.
    with file_lock:
        if not os.path.exists(file):
            return None
        with open(file, "r") as f:
            config = json.load(f)
    
    nodes = config.get("nodes", {})
    best_candidate = None
    min_load = float('inf')

    for node_id, info in nodes.items():
        # Only consider nodes that are currently HEARTBEATING
        if info.get("status") == "ONLINE":
            try:
                # Convert string load back to int for comparison
                current_load = int(info.get("load", 0))
                if current_load < min_load:
                    min_load = current_load
                    # We store IP and Port
                    best_candidate = (info.get("ip"), info.get("service port"))
            except ValueError:
                continue
    
    return best_candidate
    
def update_leader_json():
    # 1. loading or creating file
    if os.path.exists(file) and os.path.getsize(file) > 0:
        with open(file, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                config = {} 
    else:
        config = {}

    # 2. checking and initialazing nodes
    if "nodes" not in config:
        config["nodes"] = {}

    # 3. updating or creating global info
    if "cluster_info" not in config:
        config["cluster_info"] = {"last_version": 1, "leader":f"node_{self_id}", "node number":len(config['nodes'])}
    else:
        config["cluster_info"]["last_version"] += 1

    #4. updating statuses (every existing node must be setted as OFFLINE, as a new leader it is not comunicating with nobody)
    ex_node = config.get('nodes', {})
    for node_id in ex_node:
        config["nodes"][node_id]["status"] = 'OFFLINE'

    # 5. handlig leader info
        config["nodes"][f"node_{self_id}"] = {
            "status": "LEADER",
            "load":0,
            "ip": HOST,
            "port": PORT,
            "service_port": "-"
        }
    # 6. atomic overwrite
    with open(file, "w") as f:
        json.dump(config, f, indent=4,sort_keys=True)
    return config


#handling socket for service redirect as DNS style architecture for service providing
def http_dispatcher():
    #creating socket
    http_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    http_socket.bind((HOST,SERVICE_PORT))
    http_socket.listen(10)
    print(f"[INIT]http socket created successfully on {HOST}:{SERVICE_PORT}")
    while True:
        client_conn, addr = http_socket.accept()
        try:
            #reading new client request 
            request = client_conn.recv(1024).decode('utf-8')
            
            # 1. getting lower load node
            best_node = get_best_node() #returns (ip, http_port)
            
            if best_node:
                node_ip, node_port = best_node
                target = f"http://{node_ip}:{node_port}"
                
                # 2.Buildin HTTP 307 response manually
                #Browser reads this string and immidiatly redirect as code 307 is a response code for moved resurces
                response = (
                    "HTTP/1.1 307 Temporary Redirect\r\n"
                    f"Location: {target}\r\n"
                    "Content-Length: 0\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                )
            else:
                # Fallback if EVERY node is OFFLINE
                response = (
                    "HTTP/1.1 503 Service Unavailable\r\n"
                    "Content-Type: text/plain\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    "No worker nodes available." #Message shown
                )
            
            client_conn.sendall(response.encode('utf-8'))
        except Exception as e:
            print(f"[ERROR]HTTP Dispatch error: {e}")
        finally:
            client_conn.close() #after redirecting the leader will shut the connection with client


#main
# --- loading settings ---
print("[INIT]Loading settigs")
settings = load_settings()

# Vars init loaded from settings file
HOST = settings["host"]
SERVICE_PORT = settings["service_port"]      # redirect HTTP
LEADER_PORT = settings["leader_port"]        # Leader port 5000 for TCP nodes beat
file = settings["config_file_path"]          # config.json path

# fetch and modding perms
permissions = os.stat(file).st_mode
os.chmod(file, permissions | stat.S_IWRITE)

self_id = settings["self_id"]                # Leader ID

# State vars and Locks (rimangono inizializzate nel codice)
connection = 0
connection_lock = threading.Lock()
file_lock = threading.Lock()
print("[INIT]Success")
try:
    PORT = LEADER_PORT
    #json init or building (if empty it will not show leader as node, have to fix but not that necessary)
    with file_lock:
        update_leader_json()
    
    print("[Update] This node is now the leader")
    
    #launching redirect thread
    print("[INIT]Setting up service provider")
    http_thread = threading.Thread(target=http_dispatcher)
    http_thread.start()
    
    #link servers as nodes
    print("[INIT]Setting up node web")
    leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    leader_socket.bind((HOST, PORT))
    leader_socket.listen(10)
    print("[INIT]Socket created successfully. Waiting for nodes to connect...")
    
    #opening connection
    while True:    
        conn, addr = leader_socket.accept()
        with connection_lock:
            connection+=1
            print(f"[INFO] active server links: {connection}")
        #every node will be handled with a new thread
        thread = threading.Thread(target=new_server_handle,args=(conn, addr),daemon=True)
        thread.start()

    #if any error occours during the init phase it must be a reason to shut self as leader
except Exception as e:
    print(f'[ERROR]{e}: cant be leader\nLAUNCHING SELF AS SERVER')
    os.execv(sys.executable, ['python3', './server.py'])



