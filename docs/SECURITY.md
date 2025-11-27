# 🛡️ Rodovid Security Manifest

**Zero-Knowledge Architecture for Genealogy Platform**

---

## 🔐 Core Security Principles

### Zero-Knowledge Architecture

Rodovid implements a **Zero-Knowledge** architecture where:

1. **Server Never Sees Plaintext**: All personal data (names, dates, notes) is encrypted on the client before transmission
2. **Blind Storage**: Server stores only encrypted blobs (`ENC_...`)
3. **Client-Side Keys**: Encryption keys are generated and stored only on the client
4. **No Server Decryption**: Server cannot decrypt data even if compromised

---

## 🔑 Cryptographic Primitives

### Data Encryption: AES-256-GCM

- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Size**: 256 bits (32 bytes)
- **IV/Nonce**: 96 bits (12 bytes), randomly generated per encryption
- **Usage**: Encrypts all personal data (names, dates, notes)

**Format:**
```
ENC_<base64(iv + ciphertext + tag)>
```

### Key Exchange: RSA-OAEP

- **Algorithm**: RSA-OAEP (Optimal Asymmetric Encryption Padding)
- **Key Size**: 2048 bits
- **Usage**: Encrypts Tree Key for sharing between users

**Flow:**
1. Alice generates RSA keypair (public + private)
2. Bob generates RSA keypair
3. Alice encrypts her Tree Key with Bob's public key
4. Bob decrypts with his private key

### Key Derivation: PBKDF2

- **Algorithm**: PBKDF2-HMAC-SHA256
- **Iterations**: 100,000
- **Usage**: Derives recovery key from master password

---

## 📦 Data Flow

### Person Creation Flow

```
┌─────────────┐
│   CLIENT    │
│             │
│ 1. Generate │
│    Tree Key │
│    (AES-256)│
└──────┬──────┘
       │
       │ 2. Encrypt
       │    name → name_blob
       │    birth_date → birth_date_blob
       │    death_date → death_date_blob
       │
       ▼
┌─────────────┐
│   SERVER    │
│             │
│ 3. Store    │
│    blobs    │
│    (blind)  │
└─────────────┘
```

### Sharing Flow

```
┌─────────────┐                    ┌─────────────┐
│   ALICE     │                    │    BOB      │
│             │                    │             │
│ 1. Generate │                    │ 2. Generate │
│    QR Invite│                    │    RSA Pair │
└──────┬──────┘                    └──────┬──────┘
       │                                   │
       │ 3. Bob scans QR                   │
       │    & accepts                     │
       │<──────────────────────────────────┤
       │                                   │
       │ 4. Get Bob's public key          │
       │──────────────────────────────────>│
       │                                   │
       │ 5. Encrypt Tree Key              │
       │    with Bob's public key         │
       │──────────────────────────────────>│
       │                                   │
       │                                   │ 6. Decrypt
       │                                   │    with private key
       │                                   │
       │ 7. Bob can now decrypt           │
       │    Alice's encrypted blobs       │
       │<──────────────────────────────────┤
```

---

## 🔒 Field Encryption Rules

### ✅ Must Encrypt (Personal Data)

| Field | Encrypted As | Example |
|-------|--------------|---------|
| `name` | `name_blob` | `ENC_AQIDBAUG...` |
| `birth_date` | `birth_date_blob` | `ENC_FGHIJK...` |
| `death_date` | `death_date_blob` | `ENC_LMNOP...` |
| `birth_place` | `birth_place_blob` | `ENC_QRSTU...` |
| `death_place` | `death_place_blob` | `ENC_VWXYZ...` |
| `private_notes` | `private_notes_blob` | `ENC_12345...` |
| `shared_notes` | `shared_notes_blob` | `ENC_67890...` |

### ❌ Do NOT Encrypt (Structural Data)

| Field | Reason | Example |
|-------|--------|---------|
| `gender` | Needed for validation | `"M"` or `"F"` |
| `birth_year_approx` | Needed for temporal validation | `1945` |
| `death_year_approx` | Needed for temporal validation | `2015` |
| `relation` | Graph structure | `"CHILD"` |
| `link_to_id` | Graph structure | `"person_123"` |

---

## 🚫 Security Guarantees

### What Server CANNOT Do

1. ❌ **Cannot read names** - Only sees `ENC_...` blobs
2. ❌ **Cannot read dates** - Only sees `ENC_...` blobs
3. ❌ **Cannot read notes** - Only sees `ENC_...` blobs
4. ❌ **Cannot decrypt data** - No access to encryption keys
5. ❌ **Cannot see Tree Key** - Only sees RSA-encrypted wrapped key

### What Server CAN Do

1. ✅ **Validate temporal logic** - Uses `birth_year_approx` (unencrypted)
2. ✅ **Store graph structure** - Relationships are unencrypted (by design)
3. ✅ **Enforce access control** - Uses `user_id` for ownership
4. ✅ **Search metadata** - Can search by approximate years, gender

---

## 🔐 Key Management

### Tree Key (AES-256)

- **Storage**: Client-side only (IndexedDB or localStorage)
- **Generation**: Random 32 bytes
- **Lifetime**: Per family tree
- **Sharing**: Wrapped with recipient's RSA public key

### RSA Keypair

- **Storage**: 
  - Public key: Server (for sharing)
  - Private key: Client (IndexedDB) + Encrypted backup on server
- **Generation**: Client-side (Web Crypto API)
- **Lifetime**: Per user account
- **Recovery**: Encrypted with master password (PBKDF2)

---

## 🛡️ Access Control

### Ownership Model

- **Owner**: User who created the person (`user_id`)
- **Shared With**: Users who have been granted access via sharing flow
- **Guest Notes**: Shared users can add notes, but cannot edit owner's data

### Permission Levels

| Action | Owner | Shared User |
|--------|-------|-------------|
| View encrypted blobs | ✅ | ✅ (with Tree Key) |
| Edit person data | ✅ | ❌ |
| Delete person | ✅ | ❌ |
| Add guest note | ✅ | ✅ |
| View private_notes_blob | ✅ | ❌ (excluded in sharing) |

---

## 🔍 Privacy in Sharing

### What Gets Shared

- ✅ `name_blob`
- ✅ `birth_date_blob`
- ✅ `death_date_blob`
- ✅ `shared_notes_blob`
- ✅ Graph structure (relationships)

### What Does NOT Get Shared

- ❌ `private_notes_blob` - Never shared, owner-only
- ❌ Owner's Tree Key - Only wrapped copy sent to recipient

---

## ⚠️ Security Best Practices

### For Developers

1. **Never log plaintext** personal data
2. **Always validate** encrypted blob format (`ENC_...`)
3. **Never decrypt** on server (even for debugging)
4. **Use HTTPS** in production
5. **Validate user_id** on all endpoints

### For Users

1. **Backup private keys** - Store encrypted backup safely
2. **Use strong passwords** - For key recovery
3. **Verify recipients** - Before sharing Tree Key
4. **Revoke access** - If sharing is no longer needed

---

## 🧪 Security Testing

### Test Coverage

- ✅ E2E encryption/decryption
- ✅ RSA keypair generation
- ✅ Tree Key wrapping/unwrapping
- ✅ Sharing flow (Alice → Bob)
- ✅ Privacy isolation (private_notes_blob)
- ✅ Access control (IDOR prevention)

### Test Files

- `backend/test_e2e_zero_knowledge.py`
- `backend/test_security_alice_bob.py`
- `backend/test_crypto_sharing.py`
- `backend/tests/test_module_c_security.py`

---

## 📋 Compliance

### GDPR Compliance

- ✅ **Data Minimization**: Only encrypted blobs stored
- ✅ **Right to Erasure**: Users can delete all data
- ✅ **Data Portability**: Users can export encrypted data
- ✅ **Privacy by Design**: Zero-Knowledge architecture

### Ukrainian Data Protection

- ✅ **Personal Data Protection**: All data encrypted
- ✅ **Consent**: Sharing requires explicit consent
- ✅ **Access Control**: Owner controls all access

---

**Last Updated:** 2025-01-XX  
**Security Version:** 2.1.0-crypto

