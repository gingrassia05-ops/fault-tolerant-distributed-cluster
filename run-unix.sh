#!/bin/bash

# Root directory of the project
ROOT_DIR="$(pwd)"

# List of node directory names
NODES=("node1" "node2" "node3" "node4" "node5")

# Counter to assign unique numeric IDs (1, 2, 3...)
ID_COUNTER=1

echo "[SYSTEM] Starting Unix-like cluster deployment..."

for NODE in "${NODES[@]}"; do
  NODE_PATH="$ROOT_DIR/$NODE"
  
  # Create the node directory if it doesn't exist
  mkdir -p "$NODE_PATH"

  # Copy the logic files and the HTML shell into the node directory
  cp "$ROOT_DIR/server.py" "$NODE_PATH/"
  cp "$ROOT_DIR/index.html" "$NODE_PATH/"

  # Create an empty config.json to prevent FileNotFoundError on startup
  echo "{}" > "$NODE_PATH/config.json"

  # Generate settings.json dynamically for each node
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

  echo "[INIT] Node $ID_COUNTER configured in folder: $NODE"

  # Execution logic for Linux/Unix-like systems
  # Option A: Using gnome-terminal (Common on Ubuntu/Fedora)
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --title="Node $ID_COUNTER" --working-directory="$NODE_PATH" -- bash -c "python3 server.py; exec bash" &
    
  # Option B: Using xterm (Universal on almost all X11 systems)
  elif command -v xterm >/dev/null 2>&1; then
    xterm -T "Node $ID_COUNTER" -hold -e "cd $NODE_PATH && python3 server.py" &
    
  else
    echo "[WARNING] No terminal emulator found (gnome-terminal or xterm). Running in background..."
    cd "$NODE_PATH" && python3 server.py &
  fi

  # Increment ID for the next node iteration
  ((ID_COUNTER++))
done

echo "[SUCCESS] ${#NODES[@]} worker nodes are now launching in separate windows."