from flask import Flask, jsonify, request
from blockchain import Blockchain
from typing import Dict, Any
import json
from time import time

class BlockchainServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.blockchain = Blockchain()
        self.host = host
        self.port = port

        # Register routes
        self.register_routes()

    def register_routes(self):
        @self.app.route('/add_transaction', methods=['POST'])
        def add_transaction():
            try:
                transaction_data = request.get_json()
                
                # Add transaction to pending
                self.blockchain.add_transaction(transaction_data)
                
                # Mine block with pending transactions
                block = self.blockchain.mine_pending_transactions()
                
                if block:
                    response = {
                        'message': 'Transaction added successfully',
                        'block_hash': block.hash,
                        'transaction_count': len(block.transactions)
                    }
                    return jsonify(response), 200
                else:
                    return jsonify({'message': 'No transactions to mine'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/get_chain', methods=['GET'])
        def get_chain():
            chain_data = self.blockchain.export_chain()
            return chain_data, 200, {'Content-Type': 'application/json'}

        @self.app.route('/get_product_history/<batch_id>', methods=['GET'])
        def get_product_history(batch_id):
            transactions = []
            for block in self.blockchain.chain:
                for tx in block.transactions:
                    if tx.get('batch_id') == batch_id:
                        transactions.append(tx)
            return jsonify(transactions), 200

        @self.app.route('/verify_transaction/<transaction_hash>', methods=['GET'])
        def verify_transaction(transaction_hash):
            is_valid = self.blockchain.verify_transaction(transaction_hash)
            return jsonify({'exists': is_valid}), 200

        @self.app.route('/chain_status', methods=['GET'])
        def chain_status():
            return jsonify({
                'length': len(self.blockchain.chain),
                'is_valid': self.blockchain.is_chain_valid(),
                'pending_transactions': len(self.blockchain.pending_transactions)
            }), 200

    def run(self):
        self.app.run(host=self.host, port=self.port)

if __name__ == '__main__':
    blockchain_server = BlockchainServer()
    blockchain_server.run()