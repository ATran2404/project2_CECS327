# P2P Node System

A peer-to-peer node system implemented using Flask and Docker. This system allows nodes to discover each other, register with a bootstrap node, and communicate directly with each other.

## Architecture

The system consists of two main components:

1. **Bootstrap Node**: A central node that provides initial peer registration and peer list discovery.

   - Nodes register with the bootstrap node to join the network
   - The bootstrap node maintains a list of all registered peers
   - Once nodes are connected, they communicate directly with each other

2. **P2P Nodes**: Individual nodes that form the peer-to-peer network.
   - Each node has a unique ID and friendly name
   - Nodes register with the bootstrap node to join the network
   - Nodes discover other peers through the bootstrap node initially
   - Once connected, nodes communicate directly with each other
   - Nodes periodically update their peer list by communicating directly with known peers

## Features

- **Peer Discovery**: Nodes automatically discover other peers in the network
- **Direct Communication**: Nodes communicate directly with each other once connected
- **Message Verification**: Messages are verified to ensure they come from valid nodes
- **Scalability**: The system can handle dozens of nodes
- **Containerization**: All components are containerized using Docker for easy deployment

## Prerequisites

- Docker
- Docker Compose

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd p2p-system
```

2. Build and start the containers:

```bash
docker-compose up --build
```

This will start the bootstrap node and 5 P2P nodes.

## Usage

### Checking Node Status

To check the status of a node, send a GET request to its root URL:

```bash
# Check bootstrap node
curl http://localhost:5000/

# Check Node1
curl http://localhost:5001/

# Check Node2
curl http://localhost:5002/
```

### Sending Messages

To send a message from one node to another, send a POST request to the target node's `/message` endpoint:

```bash
# Send a message from Node2 to Node1
curl -X POST http://localhost:5001/message \
  -H "Content-Type: application/json" \
  -d '{"sender": "Node2", "msg": "Hello Node1!"}'
```

### Testing with Dozens of Nodes

You can test the system with dozens of nodes using the provided scripts:

#### Using PowerShell

```powershell
# Start multiple nodes
.\start_many_nodes.ps1

# Clean up
.\cleanup.ps1
```

#### Using Python

```bash
# Start nodes with default settings (20 nodes)
python test_many_nodes.py

# Start a specific number of nodes
python test_many_nodes.py 30
```

The Python script tests different communication patterns:

- Chain communication: Messages are passed from one node to the next
- Broadcast communication: One node sends a message to all other nodes
- Random communication: Nodes send messages to random peers
- Group communication: Nodes are divided into groups and communicate within their groups

## How It Works

1. **Initial Registration**:

   - When a node starts, it registers with the bootstrap node
   - The bootstrap node adds the node to its peer list
   - The node receives the list of all registered peers from the bootstrap node

2. **Peer Discovery**:

   - Nodes initially discover peers through the bootstrap node
   - Once connected, nodes discover new peers by communicating directly with known peers
   - If a node loses all its peers, it will check with the bootstrap node again

3. **Message Verification**:

   - When a node receives a message, it verifies the sender
   - The node first checks if the sender is in its direct peer list
   - If not found, it checks with the bootstrap node as a fallback
   - Messages from unverified senders are rejected

4. **Direct Communication**:
   - Once nodes are connected, they communicate directly with each other
   - The bootstrap node is only used for initial registration and peer discovery
   - Nodes maintain their own peer lists and update them by communicating directly with peers

## License

This project is licensed under the MIT License - see the LICENSE file for details.
