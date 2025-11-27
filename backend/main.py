from dotenv import load_dotenv
load_dotenv()  # Load environment variables FIRST

"""
Родовід API - Zero-Knowledge MVP
================================
FastAPI backend з E2E шифруванням.

ZERO-KNOWLEDGE ARCHITECTURE:
- Сервер зберігає ТІЛЬКИ зашифровані blob'и
- Сервер НЕ МОЖЕ прочитати персональні дані
- Структурні дані (ID, типи зв'язків) не шифруються

Endpoints:
- POST /api/v1/person - додати особу (з зашифрованими даними)
- GET /api/v1/tree - отримати дерево
- POST /api/v1/source - створити джерело
- POST /api/v1/search/magic - RAG пошук
- DELETE /api/v1/person/{id} - видалити особу
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import Enum

# Локальні модулі
from neo4j_db import get_db, Neo4jDB, MarriageStatus, MarriageType, SourceConfidence
from validators import FamilyValidator, ValidationLevel, format_validation_results
from utils.time_resolver import resolve_year

# ==================== Pydantic Models (E2E) ====================

class RelationType(str, Enum):
    PARENT = "PARENT"    # Додати батька/матір до особи
    CHILD = "CHILD"      # Додати дитину до особи
    SPOUSE = "SPOUSE"    # Додати подружжя до особи
    SIBLING = "SIBLING"  # Додати брата/сестру до особи


class PersonCreateE2E(BaseModel):
    """
    Модель для створення особи з E2E шифруванням.
    
    ZERO-KNOWLEDGE:
    - name_blob, birth_date_blob, etc. - зашифровані на клієнті
    - Сервер не може їх прочитати
    - birth_year_approx - для валідації (витягується на клієнті)
    """
    # E2E Encrypted blobs (шифруються на клієнті)
    name_blob: str = Field(..., description="Зашифроване ім'я (ENC_...)")
    birth_date_blob: Optional[str] = Field(None, description="Зашифрована дата народження")
    death_date_blob: Optional[str] = Field(None, description="Зашифроване дата смерті")
    birth_place_blob: Optional[str] = Field(None, description="Зашифроване місце народження")
    death_place_blob: Optional[str] = Field(None, description="Зашифроване місце смерті")
    private_notes_blob: Optional[str] = Field(None, description="Приватні нотатки (ніколи не sharing)")
    shared_notes_blob: Optional[str] = Field(None, description="Нотатки для sharing")
    
    # Structural data (не шифрується)
    gender: Optional[str] = Field(None, pattern="^[MF]$", description="Стать: M або F")
    
    # Approximate data for validation (витягується на клієнті перед шифруванням)
    birth_year_approx: Optional[int] = Field(None, description="Приблизний рік народження для валідації")
    death_year_approx: Optional[int] = Field(None, description="Приблизний рік смерті для валідації")
    
    # Зв'язок з існуючою особою
    link_to_id: Optional[str] = Field(None, description="ID особи до якої додаємо")
    relation: Optional[RelationType] = Field(None, description="Тип зв'язку")
    
    # Параметри шлюбу (структурні)
    marriage_year: Optional[int] = Field(None, description="Рік одруження (для валідації)")
    divorce_year: Optional[int] = Field(None, description="Рік розлучення")
    marriage_status: Optional[str] = Field("married", description="Статус шлюбу")
    marriage_type: Optional[str] = Field("civil", description="Тип шлюбу: civil/church/historical")
    
    # Sources
    source_ids: Optional[List[str]] = Field(None, description="ID джерел для прив'язки")
    
    class Config:
        extra = "ignore"


class PersonUpdate(BaseModel):
    """Модель для оновлення особи"""
    name_blob: Optional[str] = None
    birth_date_blob: Optional[str] = None
    death_date_blob: Optional[str] = None
    birth_place_blob: Optional[str] = None
    death_place_blob: Optional[str] = None
    shared_notes_blob: Optional[str] = None
    gender: Optional[str] = None
    birth_year_approx: Optional[int] = None
    death_year_approx: Optional[int] = None


class SourceCreate(BaseModel):
    """Модель для створення джерела"""
    title: str = Field(..., min_length=1, description="Назва документа/книги/архіву")
    archive_ref: Optional[str] = Field(None, description="Шифр справи (ЦДІАК, ДАЛО)")
    url: Optional[str] = Field(None, description="URL посилання")
    confidence: Optional[str] = Field("medium", description="Рівень довіри: high/medium/low")
    notes: Optional[str] = Field(None, description="Нотатки")
    from_rag: bool = Field(False, description="Знайдено через RAG")


class SourceLink(BaseModel):
    """Модель для прив'язки джерела до особи"""
    person_id: str = Field(..., description="ID особи")
    source_id: str = Field(..., description="ID джерела")
    evidence_type: str = Field("general", description="Тип: birth/death/marriage/general")


class SearchQuery(BaseModel):
    """Модель для пошуку"""
    query: str = Field(..., min_length=1, description="Пошуковий запит")
    top_k: int = Field(5, ge=1, le=20, description="Кількість результатів")


# ==================== FastAPI App ====================

app = FastAPI(
    title="Родовід API",
    description="Zero-Knowledge API з RSA/AES криптографією та QR sharing",
    version="2.1.0-crypto"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db: Optional[Neo4jDB] = None

# Validator instance
validator = FamilyValidator(strict_mode=True)

# RAG Engine (опціонально)
rag_engine = None


@app.on_event("startup")
async def startup():
    """Ініціалізація при старті"""
    global db, rag_engine
    try:
        db = get_db()
        print("✅ Neo4j готовий!")
        print("✅ Validators з TimeResolver готові!")
        
        # Спробуємо завантажити RAG (опціонально)
        try:
            from rag_engine import RAGEngine
            rag_engine = RAGEngine()
            print("✅ RAG Engine готовий!")
        except Exception as e:
            print(f"⚠️ RAG Engine недоступний: {e}")
            rag_engine = None
            
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise


# ==================== Health ====================

@app.get("/")
async def root():
    return {
        "service": "Родовід API",
        "version": "2.0.0-e2e",
        "status": "running",
        "features": {
            "e2e_encryption": True,
            "zero_knowledge": True,
            "flexible_dates": True,
            "sources": True,
            "rag": rag_engine is not None
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    neo4j_ok = False
    if db:
        try:
            with db.driver.session() as session:
                result = session.run("RETURN 1 as test")
                neo4j_ok = result.single() is not None
        except Exception as e:
            print(f"⚠️ Neo4j health check failed: {e}")
            neo4j_ok = False
    
    return {
        "status": "healthy" if neo4j_ok else "degraded",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "rag": "available" if rag_engine else "unavailable"
    }


# ==================== Person Endpoints (E2E) ====================

@app.post("/api/v1/person")
async def create_person(
    payload: PersonCreateE2E,
    user_id: str = Query("user_1", description="ID користувача")
):
    """
    Створити нову особу (E2E).
    
    ZERO-KNOWLEDGE:
    - Всі персональні дані зашифровані на клієнті
    - Сервер зберігає тільки blob'и
    - Валідація на основі birth_year_approx
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    print(f"\n{'='*60}")
    print(f"📥 POST /api/v1/person (E2E)")
    print(f"   name_blob: {payload.name_blob[:30]}..." if payload.name_blob else "   name_blob: None")
    print(f"   birth_year_approx: {payload.birth_year_approx}")
    print(f"   relation: {payload.relation}")
    print(f"   link_to_id: {payload.link_to_id}")
    print(f"{'='*60}\n")
    
    # 1. Валідація через приблизні роки
    if payload.birth_year_approx or payload.death_year_approx:
        is_valid, results = validator.validate_person(
            name="[ENCRYPTED]",  # Ми не знаємо ім'я
            birth_year=payload.birth_year_approx,
            death_year=payload.death_year_approx,
            gender=payload.gender
        )
        
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        if errors:
            print(f"❌ Validation errors: {format_validation_results(results)}")
            raise HTTPException(400, {
                "error": "Validation failed",
                "details": [str(e) for e in errors]
            })
        
        # Warnings - логуємо але дозволяємо
        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        if warnings:
            print(f"⚠️ Validation warnings: {format_validation_results(results)}")
    
    # 2. Генеруємо ID
    person_id = f"person_{uuid.uuid4().hex[:12]}"
    
    # 3. Створюємо особу в Neo4j
    try:
        person = db.create_person(
            person_id=person_id,
            user_id=user_id,
            name_blob=payload.name_blob,
            birth_date_blob=payload.birth_date_blob,
            death_date_blob=payload.death_date_blob,
            birth_place_blob=payload.birth_place_blob,
            death_place_blob=payload.death_place_blob,
            private_notes_blob=payload.private_notes_blob,
            shared_notes_blob=payload.shared_notes_blob,
            gender=payload.gender,
            birth_year_approx=payload.birth_year_approx,
            death_year_approx=payload.death_year_approx
        )
        print(f"✅ Особа створена: {person_id}")
    except Exception as e:
        print(f"❌ Neo4j error: {e}")
        raise HTTPException(500, f"Database error: {e}")
    
    # 4. Створюємо зв'язок (якщо вказано)
    if payload.link_to_id and payload.relation:
        await _create_relation(
            person_id=person_id,
            link_to_id=payload.link_to_id,
            relation=payload.relation,
            user_id=user_id,
            data=payload
        )
    
    # 5. Прив'язуємо джерела (якщо є)
    if payload.source_ids:
        for source_id in payload.source_ids:
            try:
                db.link_source_to_person(person_id, source_id, user_id)
                print(f"📎 Джерело {source_id} прив'язано до {person_id}")
            except Exception as e:
                print(f"⚠️ Не вдалося прив'язати джерело: {e}")
    
    return {
        "success": True,
        "person_id": person_id,
        "message": "Особу створено (E2E encrypted)"
    }


async def _create_relation(
    person_id: str,
    link_to_id: str,
    relation: RelationType,
    user_id: str,
    data: PersonCreateE2E
) -> None:
    """Внутрішня функція для створення зв'язків (логіка з PARTNER_PROJECT)."""
    
    # Перевіряємо чи існує особа для зв'язку
    linked_person = db.get_person(link_to_id, user_id)
    if not linked_person:
        # Можливо це root_user - створюємо
        if link_to_id.startswith("root_"):
            db.create_person(
                person_id=link_to_id,
                user_id=user_id,
                name_blob="ENC_ROOT_USER",  # Placeholder
                is_root=True
            )
            linked_person = db.get_person(link_to_id, user_id)
            print(f"✅ Створено root user: {link_to_id}")
        else:
            raise HTTPException(404, f"Person {link_to_id} not found")
    
    # Metadata для зв'язку
    relation_metadata = {}
    if data.marriage_year:
        relation_metadata["marriage_date"] = data.marriage_year
    if data.divorce_year:
        relation_metadata["divorce_year"] = data.divorce_year
    
    relation_type = relation.value.upper()
    print(f"📊 Створення зв'язку типу: {relation_type}")
    
    if relation_type == "PARENT":
        # person_id - батько, link_to_id - дитина
        # Зв'язок: БАТЬКО --[PARENT_OF]--> ДИТИНА
        print(f"   {person_id} (батько/мати) --[PARENT_OF]--> {link_to_id} (дитина)")
        db.create_relationship(person_id, link_to_id, "PARENT_OF", relation_metadata)
        
    elif relation_type == "CHILD":
        # link_to_id - батько, person_id - дитина
        # Зв'язок: БАТЬКО --[PARENT_OF]--> ДИТИНА
        print(f"   {link_to_id} (батько/мати) --[PARENT_OF]--> {person_id} (дитина)")
        db.create_relationship(link_to_id, person_id, "PARENT_OF", relation_metadata)
        
        # Автоматично створюємо sibling зв'язки
        db.auto_create_sibling_links(person_id, user_id)
        
    elif relation_type == "SPOUSE":
        # Подружжя (двонапрямлений)
        print(f"   {person_id} <--[SPOUSE]--> {link_to_id}")
        db.create_relationship(person_id, link_to_id, "SPOUSE", relation_metadata)
        db.create_relationship(link_to_id, person_id, "SPOUSE", relation_metadata)
        print(f"   ✅ SPOUSE зв'язок створений (двонапрямлений)")
        
    elif relation_type == "SIBLING":
        # Брат/сестра (двонапрямлений)
        print(f"   {person_id} <--[SIBLING]--> {link_to_id}")
        sibling_metadata = {"type": "full"}
        db.create_relationship(person_id, link_to_id, "SIBLING", sibling_metadata)
        db.create_relationship(link_to_id, person_id, "SIBLING", sibling_metadata)
        print(f"   ✅ SIBLING зв'язок створений")


@app.get("/api/v1/tree")
async def get_tree(
    user_id: str = Query("user_1"),
    include_deleted: bool = Query(True, description="Включити ghost nodes (видалені персони)")
):
    """
    Отримати повне дерево з зв'язками
    
    Args:
        user_id: ID користувача
        include_deleted: Чи показувати ghost nodes. За замовчуванням True.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    try:
        # Використовуємо існуючий метод get_tree з neo4j_db
        tree = db.get_tree(user_id, include_deleted=include_deleted)
        
        # Перетворюємо формат links -> relationships для frontend
        relationships = []
        for link in tree.get("links", []):
            relationships.append({
                "source_id": link["source"],
                "target_id": link["target"],
                "type": link["type"],
                "props": link.get("props", {})
            })
        
        return {
            "nodes": tree.get("nodes", []),
            "relationships": relationships
        }
        
    except Exception as e:
        print(f"❌ Error fetching tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/person/{person_id}")
async def get_person(
    person_id: str,
    user_id: str = Query("user_1")
):
    """Отримати особу за ID"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    person = db.get_person(person_id, user_id)
    if not person:
        raise HTTPException(404, "Person not found")
    
    # Додаємо джерела
    sources = db.get_sources_for_person(person_id, user_id)
    person["sources"] = sources
    
    return person


@app.put("/api/v1/person/{person_id}")
async def update_person(
    person_id: str,
    data: PersonUpdate,
    user_id: str = Query("user_1")
):
    """Оновити особу"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    update_data = data.dict(exclude_none=True)
    if not update_data:
        raise HTTPException(400, "No data to update")
    
    person = db.update_person(person_id, user_id, **update_data)
    if not person:
        raise HTTPException(404, "Person not found")
    
    return {"success": True, "person": person}


@app.delete("/api/v1/person/{person_id}")
async def delete_person(
    person_id: str,
    user_id: str = Query("user_1")
):
    """Видалити особу"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Не дозволяємо видаляти root
    person = db.get_person(person_id, user_id)
    if person and person.get("is_root"):
        raise HTTPException(400, "Cannot delete root user")
    
    result = db.delete_person(person_id, user_id)
    
    # Перевіряємо результат (тепер повертається Dict з action/success/message)
    if isinstance(result, dict):
        if not result.get("success"):
            raise HTTPException(404, result.get("message", "Person not found"))
        return result
    
    # Fallback для старого формату (якщо повертає bool)
    if not result:
        raise HTTPException(404, "Person not found")
    
    return {"success": True, "message": f"Person {person_id} deleted"}


@app.post("/api/v1/relationship")
async def create_relationship(
    parent_id: str = Query(..., description="ID батька/матері"),
    child_id: str = Query(..., description="ID дитини"),
    user_id: str = Query("user_1", description="ID користувача")
):
    """
    Створити зв'язок PARENT_OF між двома існуючими особами.
    Використовується для побудови дерева після створення всіх осіб.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    try:
        # Перевіряємо що обидві особи існують
        parent = db.get_person(parent_id, user_id)
        child = db.get_person(child_id, user_id)
        
        if not parent:
            raise HTTPException(404, f"Parent person {parent_id} not found")
        if not child:
            raise HTTPException(404, f"Child person {child_id} not found")
        
        # Створюємо зв'язок через add_parent
        success = db.add_parent(child_id, parent_id, user_id, is_biological=True)
        
        if not success:
            raise HTTPException(500, "Failed to create relationship")
        
        return {
            "success": True,
            "message": f"Relationship created: {parent_id} -> {child_id}",
            "parent_id": parent_id,
            "child_id": child_id,
            "relationship": "PARENT_OF"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating relationship: {e}")
        raise HTTPException(500, f"Failed to create relationship: {str(e)}")


@app.post("/api/v1/marriage")
async def create_marriage(
    person1_id: str = Query(..., description="ID першої особи"),
    person2_id: str = Query(..., description="ID другої особи"),
    user_id: str = Query("user_1", description="ID користувача"),
    data: dict = None
):
    """
    Створити шлюб (SPOUSE зв'язок) між двома особами.
    Додаткові дані: marriage_date, status (married/divorced), marriage_type
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    try:
        # Перевіряємо що обидві особи існують
        person1 = db.get_person(person1_id, user_id)
        person2 = db.get_person(person2_id, user_id)
        
        if not person1:
            raise HTTPException(404, f"Person {person1_id} not found")
        if not person2:
            raise HTTPException(404, f"Person {person2_id} not found")
        
        # Підготовка даних шлюбу
        marriage_data = data or {}
        marriage_date = marriage_data.get("marriage_date", "")
        status_str = marriage_data.get("status", "married")
        marriage_type_str = marriage_data.get("marriage_type", "civil")
        marriage_order = marriage_data.get("marriage_order", 1)
        
        # Конвертуємо strings в Enum
        try:
            status = MarriageStatus(status_str)
        except ValueError:
            status = MarriageStatus.MARRIED
        
        try:
            m_type = MarriageType(marriage_type_str)
        except ValueError:
            m_type = MarriageType.CIVIL
        
        # Витягуємо рік з дати (якщо є)
        marriage_year = None
        if marriage_date:
            try:
                marriage_year = int(marriage_date.split("-")[0])
            except (ValueError, IndexError):
                pass
        
        # Створюємо шлюб через add_spouse
        success = db.add_spouse(
            person1_id, 
            person2_id, 
            user_id,
            marriage_year=marriage_year,
            status=status,
            marriage_type=m_type,
            marriage_order=marriage_order
        )
        
        if not success:
            raise HTTPException(500, "Failed to create marriage")
        
        return {
            "success": True,
            "message": f"Marriage created: {person1_id} ↔ {person2_id}",
            "person1_id": person1_id,
            "person2_id": person2_id,
            "relationship": "SPOUSE",
            "status": status,
            "marriage_date": marriage_date
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating marriage: {e}")
        raise HTTPException(500, f"Failed to create marriage: {str(e)}")


# ==================== Source Endpoints ====================

@app.post("/api/v1/source")
async def create_source(
    data: SourceCreate,
    user_id: str = Query("user_1")
):
    """Створити джерело інформації"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    source_id = f"source_{uuid.uuid4().hex[:12]}"
    
    source = db.create_source(
        source_id=source_id,
        user_id=user_id,
        title=data.title,
        archive_ref=data.archive_ref,
        url=data.url,
        confidence=data.confidence,
        notes=data.notes,
        from_rag=data.from_rag
    )
    
    return {"success": True, "source_id": source_id, "source": source}


@app.get("/api/v1/sources")
async def get_sources(user_id: str = Query("user_1")):
    """Отримати всі джерела користувача"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    sources = db.get_all_sources(user_id)
    return {"sources": sources, "count": len(sources)}


@app.post("/api/v1/source/link")
async def link_source(
    data: SourceLink,
    user_id: str = Query("user_1")
):
    """Прив'язати джерело до особи"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    success = db.link_source_to_person(
        person_id=data.person_id,
        source_id=data.source_id,
        user_id=user_id,
        evidence_type=data.evidence_type
    )
    
    if not success:
        raise HTTPException(404, "Person or Source not found")
    
    return {"success": True, "message": f"Source linked to person"}


# ==================== RAG Search ====================

@app.post("/api/v1/search/magic")
async def search_magic(data: SearchQuery):
    """
    RAG пошук по архівах.
    
    Джерела знайдені через RAG мають from_rag=True
    """
    print(f"🔍 Пошук: '{data.query}'")
    
    if rag_engine:
        try:
            results = rag_engine.search(data.query, top_k=data.top_k)
            return {
                "success": True,
                "query": data.query,
                "results_count": len(results),
                "results": results
            }
        except Exception as e:
            print(f"❌ RAG error: {e}")
            return {
                "success": False,
                "query": data.query,
                "error": str(e),
                "results": []
            }
    else:
        # Fallback - простий пошук
        return {
            "success": True,
            "query": data.query,
            "results_count": 0,
            "results": [],
            "note": "RAG engine not available"
        }


# ==================== Validation Endpoint ====================

@app.post("/api/v1/validate/person")
async def validate_person_data(data: PersonCreateE2E):
    """
    Валідація даних без створення особи.
    Корисно для перевірки на клієнті перед відправкою.
    """
    results = []
    
    # Валідація дат
    if data.birth_year_approx or data.death_year_approx:
        is_valid, person_results = validator.validate_person(
            name="[ENCRYPTED]",
            birth_year=data.birth_year_approx,
            death_year=data.death_year_approx,
            gender=data.gender
        )
        results.extend(person_results)
    
    errors = [r for r in results if r.level == ValidationLevel.ERROR]
    warnings = [r for r in results if r.level == ValidationLevel.WARNING]
    
    return {
        "valid": len(errors) == 0,
        "errors": [{"code": r.code, "message": r.message} for r in errors],
        "warnings": [{"code": r.code, "message": r.message} for r in warnings]
    }


# ==================== Auth & Keys ====================

class UserRegister(BaseModel):
    """Модель для реєстрації з ключами"""
    user_id: str = Field(..., description="Унікальний ID користувача")
    public_key: str = Field(..., description="RSA публічний ключ (PEM)")
    encrypted_private_key_blob: Optional[str] = Field(None, description="Зашифрований приватний ключ")
    recovery_salt: Optional[str] = Field(None, description="Сіль для recovery")


class InviteCreate(BaseModel):
    """Модель для створення запрошення"""
    expires_in_hours: int = Field(24, description="Термін дії в годинах")


class InviteAccept(BaseModel):
    """Модель для прийняття запрошення"""
    invite_id: str = Field(..., description="ID запрошення з QR")


class ShareFinalize(BaseModel):
    """Модель для завершення sharing"""
    invite_id: str = Field(..., description="ID запрошення")
    encrypted_tree_key: str = Field(..., description="Tree Key, зашифрований публічним ключем одержувача")


@app.post("/api/v1/auth/register")
async def register_user(data: UserRegister):
    """
    Реєстрація користувача з криптографічними ключами.
    
    Клієнт генерує RSA пару та відправляє:
    - public_key: для sharing (відкрито)
    - encrypted_private_key_blob: для recovery (зашифровано майстер-паролем)
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Перевіряємо чи існує
    existing = db.get_user(data.user_id)
    if existing:
        raise HTTPException(400, "User already exists")
    
    user = db.create_user(
        user_id=data.user_id,
        public_key=data.public_key,
        encrypted_private_key_blob=data.encrypted_private_key_blob,
        recovery_salt=data.recovery_salt
    )
    
    if not user:
        raise HTTPException(500, "Failed to create user")
    
    print(f"✅ User registered: {data.user_id}")
    print(f"   public_key: {data.public_key[:50]}...")
    
    return {
        "success": True,
        "user_id": data.user_id,
        "message": "User registered with crypto keys"
    }


@app.get("/api/v1/auth/recovery")
async def get_recovery_data(user_id: str = Query(...)):
    """
    Отримати дані для відновлення приватного ключа.
    
    Повертає encrypted_private_key_blob та salt.
    Клієнт деривує ключ з майстер-пароля та розшифровує.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    recovery = db.get_user_recovery_data(user_id)
    if not recovery:
        raise HTTPException(404, "User not found")
    
    if not recovery.get("encrypted_private_key_blob"):
        raise HTTPException(404, "Recovery not configured")
    
    return {
        "user_id": user_id,
        "encrypted_private_key_blob": recovery["encrypted_private_key_blob"],
        "recovery_salt": recovery["recovery_salt"]
    }


@app.get("/api/v1/user/{target_user_id}/public_key")
async def get_user_public_key(target_user_id: str):
    """
    Отримати публічний ключ користувача (для sharing).
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    public_key = db.get_user_public_key(target_user_id)
    if not public_key:
        raise HTTPException(404, "User not found")
    
    return {
        "user_id": target_user_id,
        "public_key": public_key
    }


# ==================== Sharing (QR Flow) ====================

@app.post("/api/v1/share/invite")
async def create_invite(
    data: InviteCreate,
    user_id: str = Query(..., description="ID власника")
):
    """
    Крок 1: Створити запрошення (генерується QR).
    
    Повертає invite_id, який зашивається в QR-код.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Перевіряємо чи існує користувач
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    invite_id = f"inv_{uuid.uuid4().hex[:16]}"
    
    # Розраховуємо термін дії
    expires_at = (datetime.utcnow() + timedelta(hours=data.expires_in_hours)).isoformat()
    
    invite = db.create_invite(
        invite_id=invite_id,
        owner_id=user_id,
        expires_at=expires_at
    )
    
    if not invite:
        raise HTTPException(500, "Failed to create invite")
    
    print(f"🎟️ Invite created: {invite_id} by {user_id}")
    
    return {
        "success": True,
        "invite_id": invite_id,
        "qr_data": f"rodovid://share/{invite_id}",  # URL для QR
        "expires_at": expires_at
    }


@app.post("/api/v1/share/accept")
async def accept_invite(
    data: InviteAccept,
    user_id: str = Query(..., description="ID одержувача")
):
    """
    Крок 2: Прийняти запрошення (одержувач сканує QR).
    
    Одержувач відправляє свій user_id.
    Повертає дані про власника (включно з public_key).
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Перевіряємо чи існує одержувач
    recipient = db.get_user(user_id)
    if not recipient:
        raise HTTPException(404, "Recipient user not found")
    
    result = db.accept_invite(data.invite_id, user_id)
    
    if not result:
        raise HTTPException(404, "Invite not found or expired")
    
    print(f"✅ Invite {data.invite_id} accepted by {user_id}")
    
    return {
        "success": True,
        "invite_id": data.invite_id,
        "owner_id": result["owner_id"],
        "message": "Invite accepted. Waiting for owner confirmation."
    }


@app.get("/api/v1/share/pending")
async def get_pending_invites(user_id: str = Query(...)):
    """
    Отримати запрошення, що очікують підтвердження (для власника).
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    pending = db.get_pending_invites(user_id)
    
    return {
        "pending_count": len(pending),
        "invites": pending
    }


@app.post("/api/v1/share/finalize")
async def finalize_share(
    data: ShareFinalize,
    user_id: str = Query(..., description="ID власника")
):
    """
    Крок 3: Завершити sharing (власник підтверджує).
    
    Власник шифрує свій Tree Key публічним ключем одержувача
    та відправляє на сервер.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    success = db.finalize_share(
        invite_id=data.invite_id,
        owner_id=user_id,
        encrypted_tree_key=data.encrypted_tree_key
    )
    
    if not success:
        raise HTTPException(400, "Failed to finalize share")
    
    print(f"🎉 Share finalized: {data.invite_id}")
    
    return {
        "success": True,
        "message": "Share completed successfully"
    }


@app.get("/api/v1/share/shared-with-me")
async def get_shared_with_me(user_id: str = Query(...)):
    """
    Отримати список дерев, до яких є доступ.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    shares = db.get_shared_with_me(user_id)
    
    return {
        "count": len(shares),
        "shares": shares
    }


@app.get("/api/v1/share/my-shares")
async def get_my_shares(user_id: str = Query(...)):
    """
    Отримати список з ким я поділився.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    shares = db.get_my_shares(user_id)
    
    return {
        "count": len(shares),
        "shares": shares
    }


@app.delete("/api/v1/share/revoke")
async def revoke_share(
    recipient_id: str = Query(..., description="ID одержувача"),
    user_id: str = Query(..., description="ID власника")
):
    """
    Відкликати доступ.
    """
    if not db:
        raise HTTPException(500, "Database not available")
    
    success = db.revoke_share(user_id, recipient_id)
    
    if not success:
        raise HTTPException(404, "Share not found")
    
    return {"success": True, "message": f"Access revoked for {recipient_id}"}


# ==================== Stats ====================

@app.get("/api/v1/stats")
async def get_stats(user_id: str = Query("user_1")):
    """Статистика дерева"""
    if not db:
        raise HTTPException(500, "Database not available")
    
    stats = db.get_stats(user_id)
    sources = db.get_all_sources(user_id)
    
    return {
        "persons": stats["persons"],
        "relations": stats["relations"],
        "sources": len(sources)
    }


# ==================== Clear (Dev only) ====================

@app.post("/api/v1/clear")
async def clear_all(user_id: str = Query("user_1"), confirm: bool = Query(False)):
    """Очистити всі дані користувача (DEV ONLY)"""
    if not confirm:
        raise HTTPException(400, "Set confirm=true to clear data")
    
    if not db:
        raise HTTPException(500, "Database not available")
    
    # Видаляємо всіх persons
    tree = db.get_tree(user_id)
    deleted = 0
    for node in tree.get("nodes", []):
        if db.delete_person(node["id"], user_id):
            deleted += 1
    
    return {"success": True, "deleted_persons": deleted}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
