#!/usr/bin/env python3
"""SSPL Phase III - Payload Signing and Verification"""
import hashlib
import hmac
import json
import os

class PayloadSigner:
    """Signs and verifies payloads for SSPL Phase III compliance."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('SSPL_SECRET_KEY', 'default-secret-key-change-in-prod')
    
    def sign_payload(self, payload_dict: dict) -> dict:
        """Sign payload and return with signature field."""
        # Create canonical string from payload
        canonical = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'))
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Add signature to payload
        signed_payload = payload_dict.copy()
        signed_payload['signature'] = signature
        signed_payload['signature_algorithm'] = 'HMAC-SHA256'
        
        return signed_payload
    
    def verify_payload(self, payload_dict: dict, signature: str = None) -> bool:
        """Verify payload signature."""
        if signature is None:
            signature = payload_dict.get('signature')
        
        if not signature:
            return False
        
        # Remove signature fields for verification
        payload_copy = payload_dict.copy()
        payload_copy.pop('signature', None)
        payload_copy.pop('signature_algorithm', None)
        
        # Recreate canonical string
        canonical = json.dumps(payload_copy, sort_keys=True, separators=(',', ':'))
        
        # Generate expected signature
        expected_signature = hmac.new(
            self.secret_key.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(signature, expected_signature)

# Global signer instance
_signer = None

def get_signer() -> PayloadSigner:
    """Get or create global signer instance."""
    global _signer
    if _signer is None:
        _signer = PayloadSigner()
    return _signer

def sign_payload(payload_dict: dict) -> dict:
    """Convenience function to sign payload."""
    return get_signer().sign_payload(payload_dict)

def verify_payload(payload_dict: dict, signature: str = None) -> bool:
    """Convenience function to verify payload."""
    return get_signer().verify_payload(payload_dict, signature)