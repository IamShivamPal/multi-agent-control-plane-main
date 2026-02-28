#!/usr/bin/env python3
"""SSPL Phase III - Nonce Store for Replay Attack Prevention"""
import time
import json
import os
from typing import Set

class NonceStore:
    """Stores nonces to prevent replay attacks."""
    
    def __init__(self, store_file: str = 'security/nonce_store.json', ttl: int = 3600):
        self.store_file = store_file
        self.ttl = ttl  # Time-to-live in seconds
        self.nonces: Set[str] = set()
        self.nonce_timestamps = {}
        self._load_store()
    
    def _load_store(self):
        """Load nonces from file."""
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file, 'r') as f:
                    data = json.load(f)
                    self.nonces = set(data.get('nonces', []))
                    self.nonce_timestamps = data.get('timestamps', {})
                    self._cleanup_expired()
            except Exception:
                pass
    
    def _save_store(self):
        """Save nonces to file."""
        os.makedirs(os.path.dirname(self.store_file), exist_ok=True)
        with open(self.store_file, 'w') as f:
            json.dump({
                'nonces': list(self.nonces),
                'timestamps': self.nonce_timestamps
            }, f)
    
    def _cleanup_expired(self):
        """Remove expired nonces."""
        current_time = time.time()
        expired = [
            nonce for nonce, timestamp in self.nonce_timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        for nonce in expired:
            self.nonces.discard(nonce)
            self.nonce_timestamps.pop(nonce, None)
    
    def check_and_store(self, nonce: str) -> bool:
        """Check if nonce is valid and store it. Returns True if valid (not seen before)."""
        self._cleanup_expired()
        
        if nonce in self.nonces:
            return False  # Replay attack detected
        
        # Store nonce
        self.nonces.add(nonce)
        self.nonce_timestamps[nonce] = time.time()
        self._save_store()
        
        return True
    
    def is_valid(self, nonce: str) -> bool:
        """Check if nonce is valid without storing."""
        self._cleanup_expired()
        return nonce not in self.nonces

# Global nonce store instance
_nonce_store = None

def get_nonce_store() -> NonceStore:
    """Get or create global nonce store."""
    global _nonce_store
    if _nonce_store is None:
        _nonce_store = NonceStore()
    return _nonce_store

def check_nonce(nonce: str) -> bool:
    """Convenience function to check and store nonce."""
    return get_nonce_store().check_and_store(nonce)