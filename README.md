# Fault-Tolerant Distributed Cluster

A fault-tolerant distributed node cluster designed to maintain service availability through dynamic leader election, automatic failover, and persistent TCP connections.  
The project focuses on resilience, consistency, and failure management rather than service complexity.

---

## Overview

This repository contains a distributed system simulation in which multiple nodes cooperate to provide a continuous service.  
A single node acts as the **leader**, maintaining global cluster state and dispatching clients to the least-loaded worker nodes.  
If the leader or any worker node fails, the cluster automatically reorganizes itself without human intervention.

The system is intentionally designed to operate under stress conditions using **permanent TCP connections**, allowing observation of real failure scenarios and recovery behavior.

---

## Key Features

- Dynamic **leader election** with automatic promotion on failure  
- **Fault tolerance** and node failover handling  
- Persistent TCP connections with heartbeat-based monitoring  
- Best-effort **state consistency** using a synchronized JSON configuration file  
- Load-aware client dispatching  
- Real-time **HTML monitoring interface** streamed via chunked HTTP responses  
- macOS and Unix-compatible cluster bootstrap scripts  

---

## Architecture Summary

### Leader Node
- Accepts worker node registrations  
- Maintains cluster state in `config.json`  
- Routes incoming HTTP clients to the least-loaded node  

### Worker Nodes
- Maintain permanent connections with the leader  
- Serve clients via persistent HTTP connections  
- Report load and status through heartbeat messages  

### Shared State
- Stored in a JSON file synchronized across nodes  
- Updated atomically using locks to prevent corruption  

### Failover
- Nodes detect leader failure via timeouts  
- A new leader is elected automatically  
- Service continuity is preserved  

---

## Requirements

- Python 3.9+
- macOS or Linux / Unix
- No external dependencies required

---

## Installation

bash:
git clone https://github.com/gingrassia05-ops/fault-tolerant-distributed-cluster.git
cd fault-tolerant-distributed-cluster

## Configuration

Configure the cluster by editing `settings.json`.

This file defines the shared startup parameters used by all nodes in the cluster and ensures consistent initialization across the system.

Configuration options include:
- Base ports for leader and worker nodes
- Timeout thresholds for heartbeat and failure detection
- Cluster-specific runtime parameters

---

## Running the Cluster


Leader and Worker nodes can be deployed automatically using the provided scripts.

On macOS:
    chmod +x run.sh
    ./run.sh

On Linux / Unix:
    chmod +x run-unix.sh
    ./run-unix.sh

Each script opens multiple terminal sessions and launches worker nodes, simulating a distributed multi-node environment on a single machine or across multiple hosts.

## Important Notice on Cluster Startup Behavior⚠️
- The automated startup scripts do NOT explicitly start a leader node.
- All nodes are launched simultaneously and initially attempt to discover an existing leader. During this phase, connection attempts will fail by DESIGN.
- If no leader is found, nodes will retry discovery for a fixed number of attempts (default: 3, defined in `settings.json`). Once these attempts are exhausted, one node will self-elect as leader and initialize the cluster state.
- During this short initialization window, log messages indicating connection failures are expected and do not represent a malfunction.

⚠️ Please allow the discovery and election process to complete before interacting with the system
---

## Monitoring

Each worker node serves an HTML interface that exposes real-time operational data.

The interface displays:
- Active client connections
- Session identifiers
- Live updates via streamed responses over persistent TCP connections

This allows direct observation of cluster behavior under load, including connection distribution and node activity.

---

## Failure Simulation

The system is designed to be tested under failure conditions.

To simulate faults:
- Terminate a worker or leader process using CTRL+C
- Observe automatic leader election and role reassignment
- Verify that client-facing services continue operating without interruption

This manual chaos testing approach highlights the system’s resilience and recovery behavior.

---

## Design Trade-offs

The project intentionally makes several architectural trade-offs:

- Python threads and permanent connections are used for clarity and stress testing
- No TLS or cryptographic layers are implemented, as the focus is on coordination and fault tolerance
- A best-effort consistency model is adopted
- The system is not intended for production deployment

The emphasis is placed on understanding system behavior under failure rather than optimizing performance or security.

---

## Purpose

This project serves as a technical demonstration of:
- Distributed systems design principles
- Fault tolerance and failover handling
- Leader election mechanisms
- Stateful cluster coordination
- Real-world failure modeling through controlled chaos testing

---

## License
MIT License
