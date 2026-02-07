#!/bin/bash

# Root directory of the project
ROOT_DIR="$(pwd)"

# List of node directory names
NODES=("node1" "node2" "node3" "node4" "node5")

# Counter to assign unique numeric IDs (1, 2, 3...)
ID_COUNTER=1

echo "[SYSTEM] Starting cluster deployment..."

for NODE in "${NODES[@]}"; do
  NODE_PATH="$ROOT_DIR/$NODE"
  
  # Create the node directory if it doesn't exist
  mkdir -p "$NODE_PATH"

  # Copy the logic files and the HTML shell into the node directory
  # These files must exist in the ROOT_DIR
  cp "$ROOT_DIR/server.py" "$NODE_PATH/"
  cp "$ROOT_DIR/leader.py" "$NODE_PATH/"
  cp "$ROOT_DIR/index.html" "$NODE_PATH/"

  # Create an empty config.json to prevent FileNotFoundError on startup
  # This file will be overwritten by the Leader during the first heartbeat
  echo "{}" > "$NODE_PATH/config.json"

  # Generate settings.json dynamically for each node
  # self_id is incremented to ensure unique SERVICE_PORTs (6700 + ID)
  cat <<EOF > "$NODE_PATH/settings.json"
{
    "self_id": $ID_COUNTER,
    "host": "localhost",
    "leader_port": 5007,
    "service_port": 8080,
    "service_port_base": 6700,
    "config_file_path": "./config.json",
    "connection_attempts": 3,
    "timeout": 15
}
EOF

  echo "[INIT] Node $ID_COUNTER configured in folder: $NODE (Empty config.json created)"

  # Open a new macOS Terminal window, navigate to node directory, and run server.py
  osascript <<EOF
tell application "Terminal"
  do script "cd \"$NODE_PATH\" && python3 server.py"
  activate
end tell
EOF

  # Increment ID for the next node iteration
  ((ID_COUNTER++))
done

echo "[SUCCESS] ${#NODES[@]} worker nodes are now launching."
echo "[INFO] The Leader will populate config.json files upon connection."