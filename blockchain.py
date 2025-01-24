import hashlib
import json
from time import time
from typing import List, Dict, Any
import threading

class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: float, previous_hash: str):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.merkle_root = self.calculate_merkle_root()
        self.hash = self.calculate_hash()
        self._locked = False  # Internal lock flag

    def calculate_merkle_root(self) -> str:
        if not self.transactions:
            return hashlib.sha256("empty".encode()).hexdigest()
        
        hash_list = [hashlib.sha256(json.dumps(tx).encode()).hexdigest() 
                    for tx in self.transactions]
        
        while len(hash_list) > 1:
            temp_list = []
            for i in range(0, len(hash_list), 2):
                if i + 1 < len(hash_list):
                    combined = hash_list[i] + hash_list[i + 1]
                else:
                    combined = hash_list[i] + hash_list[i]
                temp_list.append(hashlib.sha256(combined.encode()).hexdigest())
            hash_list = temp_list
            
        return hash_list[0]

    def calculate_hash(self) -> str:
        block_data = {
            'index': self.index,
            'transactions': self.transactions,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'merkle_root': self.merkle_root
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def lock(self):
        """Once a block is locked, its content cannot be modified"""
        self._locked = True

    def __setattr__(self, name, value):
        """Prevent modification of attributes after block is locked"""
        if hasattr(self, '_locked') and self._locked and name != '_locked':
            raise RuntimeError("Cannot modify locked block")
        super().__setattr__(name, value)

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty = 4
        self._lock = threading.Lock()  # Thread safety
        self._chain_hash = None  # Full chain hash
        
        # Create genesis block
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, [], time(), "0")
        self._mine_block(genesis_block)
        genesis_block.lock()
        self.chain.append(genesis_block)
        self._update_chain_hash()

    def _mine_block(self, block: Block) -> None:
        """Mine a block with proof of work"""
        while not block.hash.startswith('0' * self.difficulty):
            block.nonce += 1
            block.hash = block.calculate_hash()

    def _update_chain_hash(self):
        """Update the hash of the entire chain"""
        chain_data = [block.hash for block in self.chain]
        self._chain_hash = hashlib.sha256(
            json.dumps(chain_data).encode()
        ).hexdigest()

    def add_transaction(self, transaction: Dict[str, Any]):
        """Add a new transaction to pending transactions"""
        with self._lock:
            self.pending_transactions.append({
                **transaction,
                'timestamp': time(),
                'hash': hashlib.sha256(
                    json.dumps(transaction, sort_keys=True).encode()
                ).hexdigest()
            })

    def mine_pending_transactions(self) -> Block:
        """Mine pending transactions into a new block"""
        with self._lock:
            if not self.pending_transactions:
                return None

            last_block = self.chain[-1]
            new_block = Block(
                index=last_block.index + 1,
                transactions=self.pending_transactions.copy(),
                timestamp=time(),
                previous_hash=last_block.hash
            )

            self._mine_block(new_block)
            new_block.lock()  # Lock the block after mining
            self.chain.append(new_block)
            self._update_chain_hash()
            self.pending_transactions = []
            
            return new_block

    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            # Verify current block hash
            if current_block.hash != current_block.calculate_hash():
                return False

            # Verify chain linkage
            if current_block.previous_hash != previous_block.hash:
                return False

            # Verify merkle root
            if current_block.merkle_root != current_block.calculate_merkle_root():
                return False

            # Verify proof of work
            if not current_block.hash.startswith('0' * self.difficulty):
                return False

        return True

    def verify_transaction(self, transaction_hash: str) -> bool:
        """Verify if a transaction exists in the blockchain"""
        for block in self.chain:
            for transaction in block.transactions:
                if transaction['hash'] == transaction_hash:
                    return True
        return False

    def get_block_by_hash(self, block_hash: str) -> Block:
        """Retrieve a block by its hash"""
        for block in self.chain:
            if block.hash == block_hash:
                return block
        return None

    def export_chain(self) -> str:
        """Export the entire blockchain as a JSON string"""
        chain_data = []
        for block in self.chain:
            block_data = {
                'index': block.index,
                'transactions': block.transactions,
                'timestamp': block.timestamp,
                'previous_hash': block.previous_hash,
                'hash': block.hash,
                'nonce': block.nonce,
                'merkle_root': block.merkle_root
            }
            chain_data.append(block_data)
        return json.dumps(chain_data, indent=2)