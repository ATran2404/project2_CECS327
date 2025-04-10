from flask import Flask, jsonify, request
import uuid
import requests
import logging
import threading
import time
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class Node:
    def __init__(self, host='0.0.0.0', port=5000, bootstrap_url=None, friendly_name=None):
        self.node_id = str(uuid.uuid4())
        self.friendly_name = friendly_name or f"Node-{self.node_id[:8]}"
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.peers = set()  # Set to store known peer URLs
        self.bootstrap_url = bootstrap_url or os.environ.get('BOOTSTRAP_URL', 'http://localhost:5000')
        
        # Use container name for node URL if running in Docker
        container_name = os.environ.get('HOSTNAME', 'localhost')
        self.node_url = f"http://{container_name}:{port}"
        
        # Register routes
        self.app.route('/')(self.get_node_info)
        self.app.route('/register', methods=['POST'])(self.register_peer)
        self.app.route('/message', methods=['POST'])(self.receive_message)
        self.app.route('/peers', methods=['GET'])(self.get_peers)
        
        # Start background threads
        self.discovery_thread = None
        self.heartbeat_thread = None
        
        logger.info(f"Initialized node {self.friendly_name} with ID {self.node_id}")
    
    def get_node_info(self):
        """Return basic information about the node"""
        return jsonify({
            'message': f'Node {self.friendly_name} is running!',
            'node_id': self.node_id,
            'friendly_name': self.friendly_name,
            'peers': list(self.peers)
        })
    
    def register_peer(self):
        """Register a new peer"""
        data = request.get_json()
        if not data or 'peer_url' not in data:
            return jsonify({'error': 'Missing peer_url in request'}), 400
        
        peer_url = data['peer_url']
        if peer_url != self.node_url and peer_url not in self.peers:
            self.peers.add(peer_url)
            logger.info(f"Registered new peer: {peer_url}")
            requests.post(f"{peer_url}/register", json={'peer_url': self.node_url}, timeout=5)
        return jsonify({'status': 'registered', 'peers': list(self.peers)})
    
    def verify_sender(self, sender_id):
        """Verify if a sender ID belongs to a valid node in the network"""
        # First check our direct peers
        for peer_url in self.peers:
            response = requests.get(peer_url, timeout=5)
            if response.status_code == 200:
                node_info = response.json()
                # Check both node_id and friendly_name
                if (node_info.get('node_id') == sender_id or 
                    node_info.get('friendly_name') == sender_id):
                    return True
            response = requests.get(f"{self.bootstrap_url}/peers", timeout=5)
            if response.status_code == 200:
                bootstrap_peers = response.json().get('peers', [])
            # Check each peer from bootstrap
            for peer_url in bootstrap_peers:
                if peer_url not in self.peers:  # Only check peers we don't already know
                    response = requests.get(peer_url, timeout=5)
                    if response.status_code == 200:
                        node_info = response.json()
                        # Check both node_id and friendly_name
                        if (node_info.get('node_id') == sender_id or 
                            node_info.get('friendly_name') == sender_id):
                            # Add this peer to our known peers
                            self.peers.add(peer_url)
                            return True
        # If we get here, the sender was not verified
        logger.warning(f"Could not verify sender {sender_id}")
        return False
    
    def receive_message(self):
        """Receive a message from another node"""
        data = request.get_json()
        if not data or 'sender' not in data or 'msg' not in data:
            return jsonify({'error': 'Missing sender or msg in request'}), 400
        
        sender_id = data['sender']
        message = data['msg']
        
        # Verify the sender is a valid node in the network
        if not self.verify_sender(sender_id):
            logger.warning(f"Rejected message from unverified sender: {sender_id}")
            return jsonify({'error': 'Unknown sender', 'status': 'rejected'}), 400
        
        logger.info(f"Received message from {sender_id}: {message}")
        return jsonify({'status': 'received'})
    
    def send_message(self, target_url, message):
        response = requests.post(
            f"{target_url}/message",
            json={'sender': self.node_id, 'msg': message},
            timeout=5
        )
        return response.json()
    
    def get_peers(self):
        return jsonify({'peers': list(self.peers)})
    
    def get_initial_peers_from_bootstrap(self):
        """Get the initial peer list from the bootstrap node"""
        response = requests.get(f"{self.bootstrap_url}/peers", timeout=5)
        if response.status_code == 200:
            data = response.json()
            bootstrap_peers = set(data.get('peers', []))
            logger.info(f"Received {len(bootstrap_peers)} peers from bootstrap node")
            
            # Add all peers from bootstrap to our peer list
            for peer_url in bootstrap_peers:
                if peer_url != self.node_url:
                    self.peers.add(peer_url)
            
            return True
        else:
            logger.error(f"Failed to get peers from bootstrap node: {response.text}")
            return False

    
    def register_with_bootstrap(self):
        """Register this node with the bootstrap node"""
        response = requests.post(
            f"{self.bootstrap_url}/register",
            json={'peer_url': self.node_url},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully registered with bootstrap node. Received {len(data.get('peers', []))} peers.")
            # Add all peers from bootstrap to our peer list
            for peer_url in data.get('peers', []):
                if peer_url != self.node_url:
                    self.peers.add(peer_url)
                    # Try to register with the peer as well
                    try:
                        requests.post(
                            f"{peer_url}/register",
                            json={'peer_url': self.node_url},
                            timeout=5
                        )
                    except Exception:
                        pass
        else:
            logger.error(f"Failed to register with bootstrap node: {response.text}")
    
    def discover_peers(self):
        """Periodically discover peers by communicating directly with known peers"""
        # First, get the initial peer list from the bootstrap node
        self.get_initial_peers_from_bootstrap()
        
        # Then start the periodic discovery
        while True:
            # Only check bootstrap node if we have no peers
            if len(self.peers) == 0:
                logger.info("No peers found, checking bootstrap node...")
                self.get_initial_peers_from_bootstrap()
            
            # Discover peers directly from known peers
            for peer_url in list(self.peers):
                response = requests.get(f"{peer_url}/peers", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    direct_peers = set(data.get('peers', []))
                    
                    # Add new peers
                    new_peers = direct_peers - self.peers
                    for new_peer in new_peers:
                        if new_peer != self.node_url:
                            self.peers.add(new_peer)
                            logger.info(f"Discovered new peer: {new_peer}")
                            
                            # Register with the new peer
                            try:
                                requests.post(
                                    f"{new_peer}/register",
                                    json={'peer_url': self.node_url},
                                    timeout=5
                                )
                            except Exception:
                                pass
            # Sleep for a while before next discovery
            time.sleep(5)  # Check every 5 seconds
    
    def send_heartbeat(self):
        """Periodically send heartbeat to bootstrap node to maintain registration"""
        while True:
            # Re-register with bootstrap node to indicate we're still alive
            self.register_with_bootstrap()
        # Sleep for a while before next heartbeat
            time.sleep(60)
    
    def start(self):
        """Start the node's HTTP server and background threads"""
        # Register with bootstrap node
        self.register_with_bootstrap()
        
        # Start background threads
        self.discovery_thread = threading.Thread(target=self.discover_peers, daemon=True)
        self.discovery_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
        
        logger.info(f"Starting node {self.friendly_name} on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port)

if __name__ == '__main__':
    # Create and start a new node
    bootstrap_url = os.environ.get('BOOTSTRAP_URL', 'http://localhost:5000')
    # Get friendly name from environment variable or use default
    friendly_name = os.environ.get('NODE_NAME')
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    node = Node(bootstrap_url=bootstrap_url, friendly_name=friendly_name, port=port)
    node.start()