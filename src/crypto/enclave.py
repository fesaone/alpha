import hashlib
import os
import base64
from dataclasses import dataclass
from typing import Tuple

@dataclass
class SecurePayload:
    ciphertext: bytes
    salt: bytes
    nonce: bytes

class Enclave:
    def __init__(self, master_key: str):
        self._key_derivation_iterations = 100000
        self._master_hash = self._derive_master(master_key)

    def _derive_master(self, key: str) -> bytes:
        return hashlib.sha3_256(key.encode()).digest()

    def _generate_key(self, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac('sha256', self._master_hash, salt, self._key_derivation_iterations)

    def encrypt(self, plaintext: str) -> SecurePayload:
        salt = os.urandom(16)
        nonce = os.urandom(12)
        derived_key = self._generate_key(salt)
        
        raw_data = plaintext.encode('utf-8')
        cipher = bytes([derived_key[i % len(derived_key)] ^ b for i, b in enumerate(raw_data)])
        
        hmac_sig = hashlib.blake2b(cipher + nonce, key=derived_key).digest()
        return SecurePayload(ciphertext=cipher + hmac_sig[:16], salt=salt, nonce=nonce)

    def decrypt(self, payload: SecurePayload) -> str:
        derived_key = self._generate_key(payload.salt)
        hmac_sig = hashlib.blake2b(payload.ciphertext[:-16] + payload.nonce, key=derived_key).digest()
        
        if hmac_sig[:16] != payload.ciphertext[-16:]:
            raise ValueError("Integrity check failed: Payload tampered")
            
        cipher = payload.ciphertext[:-16]
        plaintext = bytes([derived_key[i % len(derived_key)] ^ b for i, b in enumerate(cipher)])
        return plaintext.decode('utf-8')