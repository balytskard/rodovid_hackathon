# Backend - FastAPI + Neo4j

Backend сервер для платформи Родовід.

## 🚀 Запуск

```bash
# Активуйте віртуальне середовище
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Запустіть сервер
python main.py
```

Сервер запуститься на `http://localhost:8000`

## 📁 Структура

```
backend/
├── main.py              # FastAPI застосунок, API endpoints
├── neo4j_db.py          # Neo4j database layer, CRUD операції
├── validators.py        # Валідація даних (дати, імена, тощо)
├── rag_engine.py        # RAG пошук в архівах (Sentence-BERT)
├── requirements.txt     # Python залежності
├── .env                 # Налаштування (НЕ комітити!)
├── utils/
│   └── time_resolver.py # Парсинг дат різних форматів
└── tests/
    └── ...              # Unit тести
```

## 🔧 Конфігурація

Створіть `.env` файл:

```env
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=rodovid123
```

## 📡 API Endpoints

### Health Check
- `GET /` - Перевірка статусу сервера

### Tree Operations
- `GET /api/v1/tree?user_id={user_id}` - Отримати повне дерево
- `GET /api/v1/tree/stats?user_id={user_id}` - Статистика дерева

### Person Operations
- `POST /api/v1/person` - Створити особу
- `PUT /api/v1/person/{person_id}` - Оновити особу
- `DELETE /api/v1/person/{person_id}` - Видалити (перетворити в Ghost)
- `GET /api/v1/person/{person_id}` - Отримати деталі особи

### Relationship Operations
- `POST /api/v1/relationship` - Створити зв'язок (батько-дитина)
- `POST /api/v1/marriage` - Створити шлюбний зв'язок
- `DELETE /api/v1/relationship` - Видалити зв'язок

### Search
- `POST /api/v1/search/archives` - Пошук в історичних архівах

Повна документація: http://localhost:8000/docs (Swagger UI)

## 🗄 Neo4j Schema

### Node Types

**Person**
```cypher
(:Person {
  id: string,              # Унікальний ID (person_xxx або root_user_xxx)
  name_blob: string,       # Зашифроване ім'я (ENC_...)
  birth_date_blob: string, # Зашифрована дата народження
  birth_year_approx: int,  # Приблизний рік (незашифрований)
  death_year_approx: int?,
  private_notes_blob: string?,
  is_root: boolean,        # Чи це root користувач
  is_deleted: boolean,     # Ghost node
  ghost_name: string?      # Ім'я для ghost node
})
```

### Relationship Types

**PARENT_OF**
```cypher
(parent:Person)-[:PARENT_OF]->(child:Person)
```

**SPOUSE**
```cypher
(person1:Person)-[:SPOUSE {
  marriage_year: int?,
  status: string,          # MARRIED, DIVORCED, WIDOWED
  marriage_type: string    # CIVIL, RELIGIOUS, COMMON_LAW
}]-(person2:Person)
```

## 🔐 Безпека

### Шифрування
- Клієнт шифрує дані перед відправкою (AES-256-GCM)
- Сервер зберігає тільки `*_blob` поля з префіксом `ENC_`
- Сервер НЕ має ключів розшифровки
- Ключі зберігаються в браузері (IndexedDB)

### Ghost Nodes
При видаленні особи:
```python
# Замість фізичного видалення
person.is_deleted = True
person.ghost_name = "Видалена особа"
# Зв'язки зберігаються для нащадків
```

## 🧪 Тестування

```bash
# Запустіть усі тести
pytest tests/

# Конкретний тест
pytest tests/test_validators.py

# З покриттям
pytest --cov=. tests/
```

## 📦 Залежності

Основні:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `neo4j` - Database driver
- `pydantic` - Data validation
- `sentence-transformers` - Semantic search
- `chromadb` - Vector database
- `PyPDF2` - PDF parsing

Див. повний список в `requirements.txt`

## 🔨 Розробка

### Додати новий endpoint

```python
# main.py
@app.post("/api/v1/new-feature")
async def new_feature(data: FeatureRequest):
    """
    Опис нової функції
    """
    # Імплементація
    return {"status": "success"}
```

### Додати валідатор

```python
# validators.py
def validate_new_field(value: str) -> bool:
    """Валідація нового поля"""
    # Логіка валідації
    return True
```

### Запустити в режимі розробки

```bash
# Auto-reload при змінах
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🐛 Debugging

### Логування

Backend логує в консоль:
- 🔧 Конфігурацію Neo4j
- ✅ Успішні операції
- ❌ Помилки з traceback
- 📊 Статистику запитів

### Перевірка Neo4j

```cypher
// Neo4j Browser (http://localhost:7474)

// Скільки людей в базі?
MATCH (p:Person) RETURN count(p)

// Знайти root користувачів
MATCH (p:Person {is_root: true}) RETURN p

// Структура дерева
MATCH path = (p:Person)-[:PARENT_OF*]->(child:Person)
WHERE p.is_root = true
RETURN path
```

## ⚠️ Типові проблеми

**"Neo4j connection failed"**
- Перевірте чи запущений Neo4j: http://localhost:7474
- Перевірте пароль в `.env`
- Спробуйте `bolt://localhost:7687` замість `127.0.0.1`

**"Port 8000 already in use"**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**"ModuleNotFoundError"**
```bash
pip install -r requirements.txt
```
