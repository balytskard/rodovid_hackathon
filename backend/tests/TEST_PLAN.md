# 📋 ТЕСТ-ПЛАН: Кейс 7 «Родовід»

**Версія:** 1.0
**Дата:** 2025-11-27
**Автор:** QA Automation Engineer

---

## 1. Загальна Інформація

### 1.1 Об'єкт тестування
- **Backend API:** FastAPI v2.1.0-crypto
- **Database:** Neo4j Graph Database
- **Архітектура:** Zero-Knowledge E2E Encryption

### 1.2 Типи тестування
| Тип | Рівень | Інструменти |
|-----|--------|-------------|
| Unit Tests | Component | pytest |
| Integration Tests | API | pytest + httpx |
| Security Tests | E2E | pytest + Neo4j queries |
| Performance Tests | Load | pytest-benchmark |

### 1.3 Критерії входу/виходу
**Критерії входу:**
- Neo4j запущений та доступний
- Backend API працює на localhost:8000
- Всі залежності встановлені

**Критерії виходу:**
- 100% pass rate для Critical тестів
- >95% pass rate для High priority тестів
- Жоден security тест не провалений

---

## 2. Тестові Модулі

### 📦 Модуль A: Validators & TimeResolver
**Пріоритет:** Critical
**Покриття:** 20 тест-кейсів

| ID | Сценарій | Тип | Пріоритет |
|----|----------|-----|-----------|
| A-T1 | Смерть раніше народження | Negative | Critical |
| A-T2 | Батько молодший за дитину | Negative | Critical |
| A-T3 | Дитина після смерті матері | Negative | Critical |
| A-T4 | Дитина після смерті батька (+1 рік) | Warning | High |
| A-T5 | Шлюб у 5 років | Negative | Critical |
| A-T6 | Розлучення до шлюбу | Negative | Critical |
| A-TR1 | TimeResolver: "~1900" → 1900 | Positive | High |
| A-TR2 | TimeResolver: "1910..1920" → 1915 | Positive | High |
| A-TR3 | TimeResolver: "?" → Skip validation | Positive | High |
| A-C1 | Самошлюб (self-marriage) | Negative | Critical |
| A-C2 | Циклічний батько | Negative | Critical |
| A-B1 | Батько молодший 10 років | Negative | High |
| A-B2 | Мати старша 60 років | Warning | Medium |
| A-B4 | 3 біологічних батьків | Negative | Critical |
| A-M1 | Полігамія (2 активних шлюби) | Negative | Critical |

### 🌳 Модуль B: Graph Structure
**Пріоритет:** High
**Покриття:** 10 тест-кейсів

| ID | Сценарій | Тип | Пріоритет |
|----|----------|-----|-----------|
| B-1 | 5 поколінь (лінійне дерево) | Positive | Critical |
| B-2 | Half-siblings (зведені діти) | Positive | Critical |
| B-3 | Множинні шлюби (3 поспіль) | Positive | High |
| B-4 | Full-siblings визначення | Positive | High |
| B-5 | Розлучення + новий шлюб | Positive | High |
| B-6 | Церковний vs цивільний шлюб | Positive | Medium |
| B-7 | Діти без шлюбу батьків | Positive | High |
| B-8 | Вдівство (widowed status) | Positive | Medium |
| B-9 | Родина Коваленків (26 осіб) | Complex | Critical |
| B-10 | Performance: 50 вузлів <200ms | Performance | High |

### 🔐 Модуль C: Security & Zero-Knowledge
**Пріоритет:** Critical
**Покриття:** 15 тест-кейсів

| ID | Сценарій | Тип | Пріоритет |
|----|----------|-----|-----------|
| C-1 | Blind Server (blob в БД) | Security | Critical |
| C-2 | IDOR (чужа персона) | Security | Critical |
| C-3 | Cross-Sharing Attack | Security | Critical |
| C-4 | Bob НЕ може видалити дані Alice | Security | Critical |
| C-5 | Bob НЕ може редагувати дані Alice | Security | Critical |
| C-6 | Private notes ізоляція | Security | Critical |
| C-7 | Marriage type прихований | Security | High |
| C-8 | Cascade delete (OWNS) | Security | High |
| C-9 | Unshare (SHARED_WITH) | Security | High |
| C-10 | Guest notes приватність | Security | High |
| C-11 | RSA key exchange | Security | Critical |
| C-12 | AES encryption blob | Security | Critical |
| C-13 | Recovery key derivation | Security | High |
| C-14 | No PII in DB | Compliance | Critical |
| C-15 | Token expiration (invite) | Security | Medium |

### 🤝 Модуль D: Sharing & Lifecycle
**Пріоритет:** High
**Покриття:** 10 тест-кейсів

| ID | Сценарій | Тип | Пріоритет |
|----|----------|-----|-----------|
| D-1 | QR invite creation | Positive | Critical |
| D-2 | Invite acceptance | Positive | Critical |
| D-3 | Share finalization | Positive | Critical |
| D-4 | Revoke share | Positive | High |
| D-5 | Multiple shares (1 owner → N guests) | Positive | High |
| D-6 | Shared-with-me list | Positive | Medium |
| D-7 | Pending invites list | Positive | Medium |
| D-8 | Expired invite rejection | Negative | Medium |
| D-9 | Re-share prevention | Negative | High |
| D-10 | Share note with owner | Positive | Medium |

### 📜 Модуль E: Sources & RAG
**Пріоритет:** Medium
**Покриття:** 8 тест-кейсів

| ID | Сценарій | Тип | Пріоритет |
|----|----------|-----|-----------|
| E-1 | Create source | Positive | High |
| E-2 | Link source to person | Positive | High |
| E-3 | Multiple sources per person | Positive | Medium |
| E-4 | Orphan source (person deleted) | Edge Case | High |
| E-5 | Source confidence levels | Positive | Medium |
| E-6 | RAG search (якщо доступний) | Positive | Low |
| E-7 | from_rag flag | Positive | Medium |
| E-8 | Sources list | Positive | Medium |

---

## 3. Тестове Середовище

```
┌─────────────────────────────────────────────────────────────┐
│                    TEST ENVIRONMENT                         │
├─────────────────────────────────────────────────────────────┤
│  OS:          Windows 10 / Linux                           │
│  Python:      3.10+                                        │
│  Neo4j:       5.x (localhost:7687)                         │
│  Backend:     FastAPI (localhost:8000)                     │
│  Test Runner: pytest 7.x                                   │
│  Coverage:    pytest-cov                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Ризики та Мітигація

| Ризик | Ймовірність | Вплив | Мітигація |
|-------|-------------|-------|-----------|
| Neo4j недоступний | Low | Critical | Skip DB tests, run unit only |
| Test data pollution | Medium | High | Cleanup fixtures |
| Flaky tests | Medium | Medium | Retry mechanism |
| Performance variance | High | Low | Multiple runs, average |

---

## 5. Метрики та Звітність

### Pass Criteria
- **Critical:** 100% pass
- **High:** >95% pass
- **Medium:** >90% pass
- **Low:** >80% pass

### Звіти
- pytest HTML report
- Coverage report (>80% target)
- Security scan report

---

## 6. Команди Запуску

```bash
# Всі тести
pytest tests/ -v

# Тільки Critical
pytest tests/ -v -m critical

# Security тести
pytest tests/ -v -m security

# З покриттям
pytest tests/ --cov=. --cov-report=html

# Performance
pytest tests/ -v -m performance --benchmark-autosave
```

