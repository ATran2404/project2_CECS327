from flask import Flask, jsonify, request
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
peers = set()  # Set to store registered peer URLs

@app.route('/')
def get_bootstrap_info():
    """Return information about the bootstrap node"""
    return jsonify({
        'message': 'Bootstrap node is running!',
        'peers': list(peers)
    })

@app.route('/register', methods=['POST'])
def register_peer():
    """Register a new peer"""
    data = request.get_json()
    if not data or 'peer_url' not in data:
        logger.error("Missing peer_url in request")
        return jsonify({'error': 'Missing peer_url in request'}), 400
    
    peer_url = data['peer_url']
    if peer_url not in peers:
        peers.add(peer_url)
        logger.info(f"Registered new peer: {peer_url}")
        logger.info(f"Current peers: {peers}")
    
    return jsonify({'status': 'registered', 'peers': list(peers)})

@app.route('/peers', methods=['GET'])
def get_peers():
    """Return the list of registered peers"""
    logger.info(f"Returning {len(peers)} peers")
    return jsonify({'peers': list(peers)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting bootstrap node on port {port}")
    app.run(host='0.0.0.0', port=port) 