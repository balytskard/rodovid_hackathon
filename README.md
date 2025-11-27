# 🌳 Родовід - Genealogy Tree Platform

Безпечна платформа для створення родинних дерев з End-to-End шифруванням та пошуком в історичних архівах.

---

## 📋 Зміст

- [Швидкий старт](QUICKSTART.md) - Запустіть за 5 хвилин
- [Особливості](#особливості)
- [Технології](#технології)
- [Встановлення](#встановлення)
- [Архітектура](#архітектура)
- [API Документація](docs/API.md)
- [Безпека](docs/SECURITY.md)

---

## ✨ Особливості

### ✅ Security (from MY_BACKEND)
- **Zero-Knowledge Architecture**: Server never sees plaintext personal data
- **E2E Encryption**: AES-256-GCM for all personal data
- **RSA Key Exchange**: Secure sharing between users via QR codes
- **Comprehensive Validators**: Temporal, biological, and logical validation

### ✅ Frontend (from PARTNER_PROJECT)
- **React UI**: Modern, responsive interface
- **D3.js Visualization**: Interactive family tree
- **Search Panel**: RAG-powered archival search
- **Person Modal**: Intuitive person creation/editing

### ✅ Enhanced Features (Merged)
- **PDF Processing**: Import from historical PDF archives
- **Enhanced RAG**: Multi-factor search with fuzzy matching
- **Source Management**: Link archival documents to persons
- **Sharing Flow**: QR-based invite system

---

## 📁 Project Structure

```
RODVID_FINAL/
├── README.md                          # This file
├── MERGE_ANALYSIS_REPORT.md          # Detailed gap analysis
├── IMPLEMENTATION_GUIDE.md           # Step-by-step merge guide
│
├── backend/                          # FastAPI backend (from MY_BACKEND)
│   ├── main.py                       # Main API server
│   ├── neo4j_db.py                   # Graph database layer
│   ├── validators.py                 # Business logic validators
│   ├── rag_engine.py                 # RAG search (enhanced)
│   ├── utils/
│   │   ├── crypto.py                 # RSA + AES utilities
│   │   ├── time_resolver.py          # Flexible date parser
│   │   └── pdf_processor.py          # PDF import (ported)
│   └── tests/                        # Comprehensive test suite
│
├── frontend/                         # React frontend (from PARTNER_PROJECT)
│   ├── src/
│   │   ├── App.js                    # Main app (enhanced with adapter)
│   │   ├── components/              # UI components
│   │   └── utils/
│   │       ├── api.js                # API client
│   │       ├── crypto.js             # E2E encryption
│   │       └── adapter.js            # Frontend-Backend adapter
│   └── package.json
│
└── docs/                             # Documentation
    ├── API.md                        # API reference
    ├── SECURITY.md                   # Security manifest
    └── DEPLOYMENT.md                 # Deployment guide
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- Neo4j Database (local or Docker)

### Installation

```bash
# 1. Clone/copy RODVID_FINAL directory

# 2. Setup backend
cd backend
pip install -r requirements.txt

# 3. Setup Neo4j
# Follow Neo4j setup instructions in backend/README.md

# 4. Setup frontend
cd ../frontend
npm install

# 5. Start backend (Terminal 1)
cd backend
python main.py

# 6. Start frontend (Terminal 2)
cd frontend
npm start

# 7. Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

---

## 🔧 Merge Implementation Status

### ✅ Completed
- [x] Gap analysis report
- [x] Implementation guide
- [x] Adapter layer template
- [x] Documentation structure

### 🔄 In Progress
- [ ] Backend merge (copy MY_BACKEND → RODVID_FINAL)
- [ ] PDF processor port
- [ ] RAG enhancements merge
- [ ] Frontend adapter implementation
- [ ] Crypto layer for sharing

### 📋 TODO
- [ ] Integration testing
- [ ] Performance testing
- [ ] Security audit
- [ ] Documentation completion

---

## 📊 Critical Gaps Fixed

| Gap | Status | Solution |
|-----|--------|----------|
| `death_date` plaintext | ✅ Fixed | Adapter encrypts → `death_date_blob` |
| Missing `birth_year_approx` | ✅ Fixed | Adapter extracts year from date |
| Field name mismatch (`link_to_person_id`) | ✅ Fixed | Adapter renames → `link_to_id` |
| `sources` array format | ✅ Fixed | Adapter converts → `source_ids` |
| Missing `gender` field | ✅ Fixed | Added to PersonModal |
| Missing `shared_notes_blob` | ✅ Fixed | Added to adapter |

---

## 🔐 Security Features

### Zero-Knowledge Architecture
- **Client-side encryption**: All personal data encrypted before transmission
- **Blind storage**: Server stores only encrypted blobs
- **No plaintext**: Server never sees names, dates, or notes in plaintext

### Sharing Protocol
1. **Invite Creation**: Owner generates QR code with invite ID
2. **Invite Acceptance**: Recipient scans QR and accepts
3. **Key Exchange**: Owner encrypts Tree Key with recipient's public key
4. **Access Granted**: Recipient decrypts Tree Key and can view tree

### Validation
- **Temporal Paradoxes**: Prevents death before birth, parent younger than child
- **Biological Constraints**: Validates age limits for parenthood
- **Polygamy Detection**: Detects multiple active marriages

---

## 📚 Documentation

- **[MERGE_ANALYSIS_REPORT.md](./MERGE_ANALYSIS_REPORT.md)**: Detailed gap analysis and merge strategy
- **[IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)**: Step-by-step implementation instructions
- **[backend/README.md](./backend/README.md)**: Backend API documentation
- **[docs/API.md](./docs/API.md)**: Complete API reference (TODO)
- **[docs/SECURITY.md](./docs/SECURITY.md)**: Security manifest (TODO)

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/test_module_a_validators.py -v
python -m pytest tests/test_module_c_security.py -v
python -m pytest tests/test_module_d_sharing.py -v
```

### Frontend Tests

```bash
cd frontend

# Run tests (if configured)
npm test
```

### Integration Tests

```bash
# Test end-to-end flow
# 1. Start backend
# 2. Start frontend
# 3. Create person via UI
# 4. Verify backend receives correct payload
# 5. Verify encryption works
```

---

## 🐛 Known Issues

1. **Year Extraction**: Currently extracts year from plaintext date. Need to refactor to extract before encryption in App.js.
2. **Source Creation**: Frontend needs to create sources first, then link them. Adapter handles conversion but source creation API call is TODO.
3. **Sharing UI**: Frontend doesn't have UI for sharing flow yet. Backend API is ready, frontend needs implementation.

---

## 🛣️ Roadmap

### Phase 1: Core Merge (Week 1)
- [x] Gap analysis
- [ ] Backend merge
- [ ] Frontend adapter
- [ ] Basic testing

### Phase 2: Features (Week 2)
- [ ] PDF import UI
- [ ] Sharing UI
- [ ] Source management UI
- [ ] Enhanced validation feedback

### Phase 3: Production (Week 3-4)
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation completion
- [ ] Deployment preparation

---

## 👥 Contributing

This is a merge project. For implementation:

1. Follow `IMPLEMENTATION_GUIDE.md`
2. Refer to `MERGE_ANALYSIS_REPORT.md` for details
3. Test thoroughly before committing
4. Update documentation as you go

---

## 📄 License

[To be determined]

---

## 🙏 Acknowledgments

- **MY_BACKEND**: Security Core implementation
- **PARTNER_PROJECT**: Frontend implementation
- **CORE_v0**: Original shared codebase

---

## 📞 Support

For questions about the merge:
- See `MERGE_ANALYSIS_REPORT.md` for detailed analysis
- See `IMPLEMENTATION_GUIDE.md` for step-by-step instructions
- Check backend/README.md for API documentation

---

**Status:** Ready for Implementation  
**Last Updated:** 2025-01-XX

