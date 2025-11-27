"""
Криптографічний модуль для Zero-Knowledge Architecture
======================================================

Реалізує:
- RSA-2048 для обміну ключами (User Identity Keys)
- AES-256-GCM для шифрування даних (Tree Key)
- Argon2id для деривації ключа з пароля (Recovery)

УВАГА: Це серверна частина для тестування.
В продакшні вся криптографія має бути на КЛІЄНТІ!
"""

import os
import base64
import hashlib
import secrets
from typing import Tuple, Optional
from dataclasses import dataclass

# Криптографічні бібліотеки
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️ cryptography not installed. Run: pip install cryptography")


@dataclass
class RSAKeyPair:
    """Пара RSA ключів"""
    public_key_pem: str      # PEM формат для зберігання
    private_key_pem: str     # PEM формат для зберігання
    public_key_b64: str      # Base64 для передачі


@dataclass 
class EncryptedData:
    """Зашифровані дані"""
    ciphertext_b64: str      # Base64 зашифрований текст
    nonce_b64: str           # Base64 nonce (IV)


class CryptoModule:
    """
    Криптографічний модуль.
    
    Використання:
        crypto = CryptoModule()
        
        # Генерація ключів користувача
        keypair = crypto.generate_rsa_keypair()
        
        # Генерація ключа дерева
        tree_key = crypto.generate_tree_key()
        
        # Шифрування даних
        encrypted = crypto.aes_encrypt("Іван Петренко", tree_key)
        
        # Шифрування tree_key для sharing
        encrypted_key = crypto.rsa_encrypt(tree_key, recipient_public_key)
    """
    
    def __init__(self):
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography package required")
    
    # ==================== RSA (Identity Keys) ====================
    
    def generate_rsa_keypair(self, key_size: int = 2048) -> RSAKeyPair:
        """
        Генерація RSA пари ключів.
        
        Returns:
            RSAKeyPair з public та private ключами в PEM форматі
        """
        # Генеруємо приватний ключ
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Отримуємо публічний ключ
        public_key = private_key.public_key()
        
        # Серіалізуємо в PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Base64 версія публічного ключа для передачі
        public_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_b64 = base64.b64encode(public_der).decode('utf-8')
        
        return RSAKeyPair(
            public_key_pem=public_pem,
            private_key_pem=private_pem,
            public_key_b64=public_b64
        )
    
    def rsa_encrypt(self, plaintext: bytes, public_key_pem: str) -> str:
        """
        RSA шифрування (для передачі Tree Key).
        
        Args:
            plaintext: Дані для шифрування (до 190 байт для RSA-2048)
            public_key_pem: Публічний ключ одержувача в PEM
            
        Returns:
            Base64 зашифрований текст
        """
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
        
        ciphertext = public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(ciphertext).decode('utf-8')
    
    def rsa_decrypt(self, ciphertext_b64: str, private_key_pem: str) -> bytes:
        """
        RSA розшифрування.
        
        Args:
            ciphertext_b64: Base64 зашифрований текст
            private_key_pem: Приватний ключ в PEM
            
        Returns:
            Розшифровані дані
        """
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        ciphertext = base64.b64decode(ciphertext_b64)
        
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return plaintext
    
    # ==================== AES (Data Keys) ====================
    
    def generate_tree_key(self) -> bytes:
        """
        Генерація AES-256 ключа для дерева.
        
        Returns:
            32 байти (256 біт) випадкових даних
        """
        return secrets.token_bytes(32)
    
    def aes_encrypt(self, plaintext: str, key: bytes) -> EncryptedData:
        """
        AES-256-GCM шифрування.
        
        Args:
            plaintext: Текст для шифрування
            key: 32-байтний AES ключ
            
        Returns:
            EncryptedData з ciphertext та nonce
        """
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96 біт для GCM
        
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        return EncryptedData(
            ciphertext_b64=base64.b64encode(ciphertext).decode('utf-8'),
            nonce_b64=base64.b64encode(nonce).decode('utf-8')
        )
    
    def aes_decrypt(self, encrypted: EncryptedData, key: bytes) -> str:
        """
        AES-256-GCM розшифрування.
        
        Args:
            encrypted: EncryptedData з ciphertext та nonce
            key: 32-байтний AES ключ
            
        Returns:
            Розшифрований текст
        """
        aesgcm = AESGCM(key)
        
        ciphertext = base64.b64decode(encrypted.ciphertext_b64)
        nonce = base64.b64decode(encrypted.nonce_b64)
        
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
    
    def aes_encrypt_blob(self, plaintext: str, key: bytes) -> str:
        """
        Шифрування в формат ENC_... (як на фронтенді).
        
        Формат: ENC_<base64(nonce + ciphertext)>
        """
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        # Об'єднуємо nonce + ciphertext
        combined = nonce + ciphertext
        
        return "ENC_" + base64.b64encode(combined).decode('utf-8')
    
    def aes_decrypt_blob(self, blob: str, key: bytes) -> str:
        """
        Розшифрування ENC_... формату.
        """
        if not blob.startswith("ENC_"):
            raise ValueError("Invalid blob format")
        
        combined = base64.b64decode(blob[4:])
        
        nonce = combined[:12]
        ciphertext = combined[12:]
        
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode('utf-8')
    
    # ==================== Key Derivation (Recovery) ====================
    
    def derive_key_from_password(
        self, 
        password: str, 
        salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        Деривація AES ключа з пароля (для Recovery Vault).
        
        Використовує PBKDF2 (Argon2id потребує додаткову бібліотеку).
        
        Args:
            password: Майстер-пароль
            salt: Сіль (генерується якщо None)
            
        Returns:
            (derived_key, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 біт
            salt=salt,
            iterations=100000,  # Рекомендовано OWASP
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        
        return key, salt
    
    def encrypt_private_key(
        self, 
        private_key_pem: str, 
        master_password: str
    ) -> Tuple[str, str]:
        """
        Шифрування приватного ключа для Recovery Vault.
        
        Args:
            private_key_pem: Приватний ключ в PEM
            master_password: Майстер-пароль
            
        Returns:
            (encrypted_blob, salt_b64)
        """
        # Деривуємо ключ з пароля
        derived_key, salt = self.derive_key_from_password(master_password)
        
        # Шифруємо приватний ключ
        encrypted = self.aes_encrypt(private_key_pem, derived_key)
        
        # Об'єднуємо nonce + ciphertext
        combined = base64.b64decode(encrypted.nonce_b64) + base64.b64decode(encrypted.ciphertext_b64)
        
        return (
            base64.b64encode(combined).decode('utf-8'),
            base64.b64encode(salt).decode('utf-8')
        )
    
    def decrypt_private_key(
        self,
        encrypted_blob: str,
        salt_b64: str,
        master_password: str
    ) -> str:
        """
        Розшифрування приватного ключа з Recovery Vault.
        
        Args:
            encrypted_blob: Зашифрований приватний ключ
            salt_b64: Сіль в Base64
            master_password: Майстер-пароль
            
        Returns:
            Приватний ключ в PEM
        """
        # Деривуємо ключ з пароля
        salt = base64.b64decode(salt_b64)
        derived_key, _ = self.derive_key_from_password(master_password, salt)
        
        # Розділяємо nonce + ciphertext
        combined = base64.b64decode(encrypted_blob)
        nonce = combined[:12]
        ciphertext = combined[12:]
        
        encrypted = EncryptedData(
            ciphertext_b64=base64.b64encode(ciphertext).decode('utf-8'),
            nonce_b64=base64.b64encode(nonce).decode('utf-8')
        )
        
        return self.aes_decrypt(encrypted, derived_key)


# Singleton instance
_crypto: Optional[CryptoModule] = None

def get_crypto() -> CryptoModule:
    """Отримати екземпляр CryptoModule"""
    global _crypto
    if _crypto is None:
        _crypto = CryptoModule()
    return _crypto

