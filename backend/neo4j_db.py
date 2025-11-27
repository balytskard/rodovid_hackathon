"""
Neo4j Graph Database for Rodovid Family Tree
=============================================
Чиста реалізація графової бази для родинного дерева.

Підтримує:
- 4-5+ поколінь
- Множинні шлюби
- Зведені брати/сестри
- Розлучення
"""

import os
from typing import Optional, List, Dict, Any
from enum import Enum
from dotenv import load_dotenv

# Завантажити змінні середовища з .env файлу
load_dotenv()

# Neo4j driver
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️ Neo4j package not installed. Run: pip install neo4j")


class RelationType(str, Enum):
    """Типи зв'язків між особами"""
    PARENT_OF = "PARENT_OF"      # Батько/мати → дитина
    CHILD_OF = "CHILD_OF"        # Дитина → батько/мати
    SPOUSE = "SPOUSE"            # Подружжя (двосторонній)
    SIBLING = "SIBLING"          # Брат/сестра


class MarriageStatus(str, Enum):
    """Статус шлюбу"""
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"


class MarriageType(str, Enum):
    """Тип шлюбу"""
    CIVIL = "civil"          # Цивільний (РАЦС)
    CHURCH = "church"        # Церковний (вінчання)
    HISTORICAL = "historical" # Історичний (з архівів, тип невідомий)


class SiblingType(str, Enum):
    """Тип братів/сестер"""
    FULL = "full"    # Обидва батьки спільні
    HALF = "half"    # Один батько спільний


class SourceConfidence(str, Enum):
    """Рівень довіри до джерела"""
    HIGH = "high"      # Офіційний документ (метрика, свідоцтво)
    MEDIUM = "medium"  # Напівофіційне (церковна книга)
    LOW = "low"        # Усний переказ, спогади


class Neo4jDB:
    """
    Головний клас для роботи з Neo4j.
    
    Структура графу:
    - (Person) - вузол особи
    - [:PARENT_OF] - зв'язок батько→дитина
    - [:CHILD_OF] - зв'язок дитина→батько
    - [:SPOUSE] - зв'язок подружжя (з властивостями marriage_order, status)
    - [:SIBLING] - зв'язок брат/сестра (з властивістю type: full/half)
    """
    
    def __init__(self):
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j package not installed")
        
        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "rodovid123")
        
        print(f"\n🔧 Neo4j Configuration:")
        print(f"   URI: {uri}")
        print(f"   User: {user}")
        print(f"   Password: {'*' * len(password)}")
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self._verify_connection()
        except Exception as e:
            print(f"\n❌ FATAL: Neo4j connection failed!")
            print(f"   URI: {uri}")
            print(f"   User: {user}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")
            print(f"\n💡 Troubleshooting:")
            print(f"   1. Is Neo4j running? Check: docker ps (if using Docker)")
            print(f"   2. Is .env file present in backend/ directory?")
            print(f"   3. Try: python backend/debug_db.py")
            raise
    
    def _verify_connection(self):
        """Перевірка з'єднання з Neo4j"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                if record and record["test"] == 1:
                    print("✅ Neo4j connected successfully")
                else:
                    raise Exception("Connection test failed")
        except Exception as e:
            print(f"❌ Neo4j connection verification failed:")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def close(self):
        """Закрити з'єднання"""
        self.driver.close()
    
    # ==================== CRUD для Person ====================
    
    def create_person(
        self,
        person_id: str,
        user_id: str,
        # E2E Encrypted fields (зашифровані на клієнті)
        name_blob: Optional[str] = None,           # ENC_... зашифроване ім'я
        birth_date_blob: Optional[str] = None,     # ENC_... зашифрована дата народження
        death_date_blob: Optional[str] = None,     # ENC_... зашифрована дата смерті
        birth_place_blob: Optional[str] = None,    # ENC_... зашифроване місце народження
        death_place_blob: Optional[str] = None,    # ENC_... зашифроване місце смерті
        private_notes_blob: Optional[str] = None,  # ENC_... приватні нотатки (ніколи не передаються)
        shared_notes_blob: Optional[str] = None,   # ENC_... нотатки для sharing
        # Structural fields (не шифруються - потрібні для графу)
        gender: Optional[str] = None,              # 'M' або 'F'
        is_root: bool = False,
        # Metadata для валідації (зберігається окремо для валідаторів)
        birth_year_approx: Optional[int] = None,   # Приблизний рік для валідації
        death_year_approx: Optional[int] = None,   # Приблизний рік для валідації
    ) -> Dict[str, Any]:
        """
        Створити нову особу з E2E шифруванням.
        
        SECURITY:
        - Створюється зв'язок [:OWNS] від User до Person
        - Тільки власник (OWNS) може редагувати/видаляти
        - Гості (SHARED_WITH) мають read-only доступ
        
        Args:
            person_id: Унікальний ID особи
            user_id: ID власника дерева
            ...
        
        Returns:
            Створена особа
        """
        with self.driver.session() as session:
            # Створюємо Person та зв'язок OWNS
            result = session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (p:Person {
                    id: $person_id,
                    name_blob: $name_blob,
                    birth_date_blob: $birth_date_blob,
                    death_date_blob: $death_date_blob,
                    birth_place_blob: $birth_place_blob,
                    death_place_blob: $death_place_blob,
                    private_notes_blob: $private_notes_blob,
                    shared_notes_blob: $shared_notes_blob,
                    gender: $gender,
                    is_root: $is_root,
                    birth_year_approx: $birth_year_approx,
                    death_year_approx: $death_year_approx,
                    is_deleted: false,
                    created_at: datetime()
                })
                CREATE (u)-[:OWNS]->(p)
                RETURN p
            """, 
                person_id=person_id,
                user_id=user_id,
                name_blob=name_blob,
                birth_date_blob=birth_date_blob,
                death_date_blob=death_date_blob,
                birth_place_blob=birth_place_blob,
                death_place_blob=death_place_blob,
                private_notes_blob=private_notes_blob,
                shared_notes_blob=shared_notes_blob,
                gender=gender,
                is_root=is_root,
                birth_year_approx=birth_year_approx,
                death_year_approx=death_year_approx
            )
            record = result.single()
            if record:
                person = dict(record["p"])
                person["owner_id"] = user_id  # Додаємо для зручності
                return person
            
            # Якщо User не існує - створюємо Person без зв'язку (fallback для тестів)
            result = session.run("""
                CREATE (p:Person {
                    id: $person_id,
                    user_id: $user_id,
                    name_blob: $name_blob,
                    birth_date_blob: $birth_date_blob,
                    death_date_blob: $death_date_blob,
                    birth_place_blob: $birth_place_blob,
                    death_place_blob: $death_place_blob,
                    private_notes_blob: $private_notes_blob,
                    shared_notes_blob: $shared_notes_blob,
                    gender: $gender,
                    is_root: $is_root,
                    birth_year_approx: $birth_year_approx,
                    death_year_approx: $death_year_approx,
                    is_deleted: false,
                    created_at: datetime()
                })
                RETURN p
            """, 
                person_id=person_id,
                user_id=user_id,
                name_blob=name_blob,
                birth_date_blob=birth_date_blob,
                death_date_blob=death_date_blob,
                birth_place_blob=birth_place_blob,
                death_place_blob=death_place_blob,
                private_notes_blob=private_notes_blob,
                shared_notes_blob=shared_notes_blob,
                gender=gender,
                is_root=is_root,
                birth_year_approx=birth_year_approx,
                death_year_approx=death_year_approx
            )
            record = result.single()
            return dict(record["p"]) if record else None
    
    def get_person(self, person_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Отримати особу за ID.
        
        SECURITY: Повертає персону якщо user є власником (OWNS) або гостем (SHARED_WITH).
        """
        with self.driver.session() as session:
            # Спробуємо через OWNS або SHARED_WITH
            result = session.run("""
                MATCH (u:User {id: $user_id})
                MATCH (p:Person {id: $person_id})
                WHERE (u)-[:OWNS]->(p) OR (u)-[:SHARED_WITH]->(p)
                OPTIONAL MATCH (owner:User)-[:OWNS]->(p)
                RETURN p, 
                       EXISTS((u)-[:OWNS]->(p)) as is_owner,
                       owner.id as owner_id
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if record:
                person = dict(record["p"])
                person["is_owner"] = record["is_owner"]
                person["owner_id"] = record["owner_id"]
                return person
            
            # Fallback - шукаємо через user_id в полі (для простих випадків без User node)
            result = session.run("""
                MATCH (p:Person {id: $person_id})
                WHERE p.user_id = $user_id OR p.owner_id = $user_id
                RETURN p
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            if record:
                person = dict(record["p"])
                person["is_owner"] = True
                return person
            
            return None
    
    def update_person(self, person_id: str, user_id: str, **props) -> Optional[Dict[str, Any]]:
        """
        Оновити дані особи.
        
        SECURITY: Тільки ВЛАСНИК (OWNS) може редагувати!
        Гість (SHARED_WITH) отримає None.
        """
        updates = {k: v for k, v in props.items() if v is not None}
        if not updates:
            return self.get_person(person_id, user_id)
        
        set_clause = ", ".join([f"p.{k} = ${k}" for k in updates.keys()])
        
        with self.driver.session() as session:
            # Тільки власник може оновлювати
            result = session.run(f"""
                MATCH (u:User {{id: $user_id}})-[:OWNS]->(p:Person {{id: $person_id}})
                SET {set_clause}, p.updated_at = datetime()
                RETURN p
            """, person_id=person_id, user_id=user_id, **updates)
            record = result.single()
            
            if record:
                return dict(record["p"])
            
            # Fallback для старого формату
            result = session.run(f"""
                MATCH (p:Person {{id: $person_id, owner_id: $user_id}})
                SET {set_clause}, p.updated_at = datetime()
                RETURN p
            """, person_id=person_id, user_id=user_id, **updates)
            record = result.single()
            return dict(record["p"]) if record else None
    
    def _generate_ghost_name(self, person_id: str, user_id: str) -> str:
        """
        Генерувати автоматичне ім'я для ghost node на основі зв'язків.
        
        Логіка:
        - Знаходимо листові персони (без нащадків) як "root" точки
        - Визначаємо відстань (покоління) від найближчого листа до ghost
        - Визначаємо стать ghost node
        - Генеруємо назву:
          * 1 покоління: дід/баба
          * 2 покоління: прадід/прабаба
          * 3 покоління: двоюрідний дід/двоюрідна баба
          * 4+ покоління: родич N коліна / родичка N коліна
        
        Returns:
            Українська назва (не шифрована, без ENC_)
        """
        with self.driver.session() as session:
            # Знаходимо будь-яку персону без CHILD_OF зв'язків (листовий вузол) як референс
            result = session.run("""
                MATCH (leaf:Person {user_id: $user_id})
                WHERE NOT (leaf)<-[:PARENT_OF]-()
                WITH leaf LIMIT 1
                MATCH (ghost:Person {id: $person_id})
                MATCH path = shortestPath((ghost)-[*]-(leaf))
                RETURN ghost.gender as gender, length(path) as distance
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if not record:
                # Fallback: просто родич/родичка
                result_fallback = session.run("""
                    MATCH (p:Person {id: $person_id})
                    RETURN p.gender as gender
                """, person_id=person_id)
                rec = result_fallback.single()
                gender = rec.get("gender", "M") if rec else "M"
                return "родич" if gender == "M" else "родичка"
            
            gender = record.get("gender", "M")
            distance = record.get("distance", 0)
            
            # Генеруємо назву на основі відстані та статі
            if distance == 1:
                return "дід" if gender == "M" else "баба"
            elif distance == 2:
                return "прадід" if gender == "M" else "прабаба"
            elif distance == 3:
                return "двоюрідний дід" if gender == "M" else "двоюрідна баба"
            else:
                # 4+ покоління
                generation = distance - 1
                return f"родич {generation} коліна" if gender == "M" else f"родичка {generation} коліна"
    
    def delete_person(self, person_id: str, user_id: str) -> Dict[str, Any]:
        """
        Видалити особу або перетворити на ghost node.
        
        ЛОГІКА GHOST NODES:
        - Якщо персона має нащадків (вихідні PARENT_OF зв'язки): is_deleted=True (ghost)
        - Якщо персона НЕ має нащадків: DETACH DELETE (повне видалення)
        
        SECURITY:
        - Якщо OWNS: Може видалити/ghost
        - Якщо SHARED_WITH: Видаляє тільки зв'язок (прибрати з виду)
        
        Returns:
            {"action": "ghosted"|"deleted"|"unshared"|"not_found", "success": bool}
        """
        with self.driver.session() as session:
            # 1. Перевіряємо чи є власником
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p:Person {id: $person_id})
                OPTIONAL MATCH (p)-[r:PARENT_OF]->()
                WITH p, count(r) as descendants_count
                RETURN p, descendants_count
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if record:
                descendants = record["descendants_count"]
                
                if descendants > 0:
                    # Є нащадки → Ghost node з автоматичною назвою
                    ghost_name = self._generate_ghost_name(person_id, user_id)
                    session.run("""
                        MATCH (p:Person {id: $person_id})
                        SET p.is_deleted = true, 
                            p.deleted_at = datetime(),
                            p.ghost_name = $ghost_name
                    """, person_id=person_id, ghost_name=ghost_name)
                    return {
                        "action": "ghosted",
                        "success": True,
                        "message": f"Person converted to ghost '{ghost_name}' (has {descendants} descendants)"
                    }
                else:
                    # Немає нащадків → Повне видалення
                    session.run("""
                        MATCH (p:Person {id: $person_id})
                        DETACH DELETE p
                    """, person_id=person_id)
                    return {
                        "action": "deleted",
                        "success": True,
                        "message": "Person and all relations deleted"
                    }
            
            # 2. Перевіряємо чи є гостем (SHARED_WITH)
            result = session.run("""
                MATCH (u:User {id: $user_id})-[r:SHARED_WITH]->(p:Person {id: $person_id})
                DELETE r
                RETURN count(r) as unshared
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if record and record["unshared"] > 0:
                return {"action": "unshared", "success": True, "message": "Removed from your view (original preserved)"}
            
            # 3. Fallback для старого формату (owner_id в полі)
            result = session.run("""
                MATCH (p:Person {id: $person_id, owner_id: $user_id})
                OPTIONAL MATCH (p)-[r:PARENT_OF]->()
                WITH p, count(r) as descendants_count
                RETURN p, descendants_count
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if record:
                descendants = record["descendants_count"]
                
                if descendants > 0:
                    # Ghost для fallback з назвою
                    ghost_name = self._generate_ghost_name(person_id, user_id)
                    session.run("""
                        MATCH (p:Person {id: $person_id})
                        SET p.is_deleted = true, 
                            p.deleted_at = datetime(),
                            p.ghost_name = $ghost_name
                    """, person_id=person_id, ghost_name=ghost_name)
                    return {
                        "action": "ghosted",
                        "success": True,
                        "message": f"Person converted to ghost '{ghost_name}' (legacy, {descendants} descendants)"
                    }
                else:
                    # Видалення для fallback
                    session.run("""
                        MATCH (p:Person {id: $person_id, owner_id: $user_id})
                        DETACH DELETE p
                    """, person_id=person_id, user_id=user_id)
                    return {"action": "deleted", "success": True, "message": "Person deleted (legacy mode)"}
            
            # 4. Fallback для нового формату (user_id в полі, без User node)
            result = session.run("""
                MATCH (p:Person {id: $person_id, user_id: $user_id})
                OPTIONAL MATCH (p)-[r:PARENT_OF]->()
                WITH p, count(r) as descendants_count
                RETURN p, descendants_count
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if record:
                descendants = record["descendants_count"]
                
                if descendants > 0:
                    # Ghost для user_id fallback
                    ghost_name = self._generate_ghost_name(person_id, user_id)
                    session.run("""
                        MATCH (p:Person {id: $person_id})
                        SET p.is_deleted = true, 
                            p.deleted_at = datetime(),
                            p.ghost_name = $ghost_name
                    """, person_id=person_id, ghost_name=ghost_name)
                    return {
                        "action": "ghosted",
                        "success": True,
                        "message": f"Person converted to ghost '{ghost_name}' (user_id mode, {descendants} descendants)"
                    }
                else:
                    # Видалення для user_id fallback
                    session.run("""
                        MATCH (p:Person {id: $person_id, user_id: $user_id})
                        DETACH DELETE p
                    """, person_id=person_id, user_id=user_id)
                    return {"action": "deleted", "success": True, "message": "Person deleted (user_id mode)"}
            
            return {"action": "not_found", "success": False, "message": "Person not found or access denied"}
    
    def check_ownership(self, person_id: str, user_id: str) -> str:
        """
        Перевірити тип доступу до персони.
        
        Returns:
            "owner" | "guest" | "none"
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})
                MATCH (p:Person {id: $person_id})
                RETURN 
                    EXISTS((u)-[:OWNS]->(p)) as is_owner,
                    EXISTS((u)-[:SHARED_WITH]->(p)) as is_guest
            """, person_id=person_id, user_id=user_id)
            record = result.single()
            
            if not record:
                return "none"
            if record["is_owner"]:
                return "owner"
            if record["is_guest"]:
                return "guest"
            return "none"
    
    # ==================== Зв'язки ====================
    
    def add_parent(
        self,
        child_id: str,
        parent_id: str,
        user_id: str,
        is_biological: bool = True
    ) -> bool:
        """
        Додати батьківський зв'язок.
        Створює двосторонній зв'язок: parent -[PARENT_OF]-> child та child -[CHILD_OF]-> parent
        
        Args:
            child_id: ID дитини
            parent_id: ID батька/матері
            user_id: ID власника дерева
            is_biological: Чи біологічний (True) чи всиновлення (False)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (parent:Person {id: $parent_id, user_id: $user_id})
                MATCH (child:Person {id: $child_id, user_id: $user_id})
                MERGE (parent)-[r1:PARENT_OF {is_biological: $is_biological}]->(child)
                MERGE (child)-[r2:CHILD_OF {is_biological: $is_biological}]->(parent)
                RETURN parent, child
            """, parent_id=parent_id, child_id=child_id, user_id=user_id, is_biological=is_biological)
            return result.single() is not None
    
    def add_spouse(
        self,
        person1_id: str,
        person2_id: str,
        user_id: str,
        marriage_year: Optional[int] = None,
        divorce_year: Optional[int] = None,
        status: MarriageStatus = MarriageStatus.MARRIED,
        marriage_type: "MarriageType" = None,
        marriage_order: int = 1
    ) -> bool:
        """
        Додати зв'язок подружжя (ТІЛЬКИ офіційний шлюб або вінчання).
        Створює двосторонній зв'язок SPOUSE.
        
        Args:
            person1_id: ID першої особи
            person2_id: ID другої особи
            marriage_year: Рік одруження
            divorce_year: Рік розлучення (якщо є)
            status: Статус шлюбу (married/divorced/widowed)
            marriage_type: Тип шлюбу (civil/church/historical)
            marriage_order: Порядковий номер шлюбу (1, 2, 3...)
        
        Note:
            Якщо батьки НЕ одружені - не викликати цей метод!
            Просто додати обох як PARENT_OF до дитини.
        """
        # Default marriage type
        if marriage_type is None:
            from neo4j_db import MarriageType
            marriage_type = MarriageType.CIVIL
        
        with self.driver.session() as session:
            # Спробуємо через OWNS
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p1:Person {id: $person1_id})
                MATCH (u)-[:OWNS]->(p2:Person {id: $person2_id})
                MERGE (p1)-[r1:SPOUSE]->(p2)
                MERGE (p2)-[r2:SPOUSE]->(p1)
                SET r1.status = $status,
                    r1.marriage_order = $marriage_order,
                    r1.marriage_type = $marriage_type,
                    r2.status = $status,
                    r2.marriage_order = $marriage_order,
                    r2.marriage_type = $marriage_type
                RETURN p1, p2
            """, 
                person1_id=person1_id, 
                person2_id=person2_id, 
                user_id=user_id,
                status=status.value if hasattr(status, 'value') else status,
                marriage_order=marriage_order,
                marriage_type=marriage_type.value if hasattr(marriage_type, 'value') else marriage_type
            )
            
            record = result.single()
            
            # Fallback для старого формату
            if record is None:
                result = session.run("""
                    MATCH (p1:Person {id: $person1_id})
                    MATCH (p2:Person {id: $person2_id})
                    WHERE (p1.owner_id = $user_id OR p1.user_id = $user_id)
                    AND (p2.owner_id = $user_id OR p2.user_id = $user_id)
                    MERGE (p1)-[r1:SPOUSE]->(p2)
                    MERGE (p2)-[r2:SPOUSE]->(p1)
                    SET r1.status = $status,
                        r1.marriage_order = $marriage_order,
                        r1.marriage_type = $marriage_type,
                        r2.status = $status,
                        r2.marriage_order = $marriage_order,
                        r2.marriage_type = $marriage_type
                    RETURN p1, p2
                """, 
                    person1_id=person1_id, 
                    person2_id=person2_id, 
                    user_id=user_id,
                    status=status.value if hasattr(status, 'value') else status,
                    marriage_order=marriage_order,
                    marriage_type=marriage_type.value if hasattr(marriage_type, 'value') else marriage_type
                )
                record = result.single()
            
            if record is None:
                return False
            
            # Додаємо опціональні властивості окремо
            if marriage_year is not None:
                session.run("""
                    MATCH (p1:Person {id: $person1_id})-[r:SPOUSE]-(p2:Person {id: $person2_id})
                    SET r.marriage_year = $marriage_year
                """, person1_id=person1_id, person2_id=person2_id, marriage_year=marriage_year)
            
            if divorce_year is not None:
                session.run("""
                    MATCH (p1:Person {id: $person1_id})-[r:SPOUSE]-(p2:Person {id: $person2_id})
                    SET r.divorce_year = $divorce_year
                """, person1_id=person1_id, person2_id=person2_id, divorce_year=divorce_year)
            
            return True
    
    def add_sibling(
        self,
        person1_id: str,
        person2_id: str,
        user_id: str,
        sibling_type: SiblingType = SiblingType.FULL
    ) -> bool:
        """
        Додати зв'язок брат/сестра.
        
        Args:
            sibling_type: 'full' (обидва батьки спільні) або 'half' (один батько спільний)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p1:Person {id: $person1_id, user_id: $user_id})
                MATCH (p2:Person {id: $person2_id, user_id: $user_id})
                MERGE (p1)-[r1:SIBLING {type: $sibling_type}]->(p2)
                MERGE (p2)-[r2:SIBLING {type: $sibling_type}]->(p1)
                RETURN p1, p2
            """, 
                person1_id=person1_id, 
                person2_id=person2_id, 
                user_id=user_id,
                sibling_type=sibling_type.value
            )
            return result.single() is not None
    
    # ==================== Отримання дерева ====================
    
    def get_tree(self, user_id: str, include_deleted: bool = True) -> Dict[str, Any]:
        """
        Отримати дерево користувача (OWNS + SHARED_WITH).
        
        SECURITY:
        - Повертає персони через OWNS (власні)
        - Повертає персони через SHARED_WITH (чужі, до яких є доступ)
        - Для SHARED_WITH не повертаємо private_notes_blob
        
        Args:
            user_id: ID користувача
            include_deleted: Чи включати ghost nodes (is_deleted=true). За замовчуванням True.
        
        Returns:
            {
                "nodes": [...],
                "links": [...]
            }
        """
        with self.driver.session() as session:
            # Отримати всі вузли (OWNS + SHARED_WITH) з опціональною фільтрацією ghost
            deleted_filter = "" if include_deleted else "AND (item.person.is_deleted IS NULL OR item.person.is_deleted = false)"
            
            nodes_result = session.run(f"""
                MATCH (u:User {{id: $user_id}})
                OPTIONAL MATCH (u)-[:OWNS]->(owned:Person)
                OPTIONAL MATCH (u)-[sw:SHARED_WITH]->(shared:Person)
                WITH collect(DISTINCT {{
                    person: owned, 
                    is_owner: true,
                    guest_note: null
                }}) + collect(DISTINCT {{
                    person: shared, 
                    is_owner: false,
                    guest_note: sw.guest_note_blob
                }}) as all_persons
                UNWIND all_persons as item
                WITH item
                WHERE item.person IS NOT NULL {deleted_filter}
                RETURN item.person as p, item.is_owner as is_owner, item.guest_note as guest_note
            """, user_id=user_id)
            
            nodes = []
            person_ids = set()
            
            for record in nodes_result:
                if record["p"] is None:
                    continue
                    
                node = dict(record["p"])
                node["is_owner"] = record["is_owner"]
                
                # Видаляємо приватні нотатки для чужих персон
                if not record["is_owner"]:
                    node.pop("private_notes_blob", None)
                    # Додаємо нотатку гостя якщо є
                    if record["guest_note"]:
                        node["my_guest_note_blob"] = record["guest_note"]
                
                # Конвертуємо datetime
                for key in ['created_at', 'updated_at']:
                    if key in node and node[key]:
                        node[key] = str(node[key])
                
                if node["id"] not in person_ids:
                    nodes.append(node)
                    person_ids.add(node["id"])
            
            # Fallback для старого формату (user_id в полі Person)
            if not nodes:
                nodes_result = session.run("""
                    MATCH (p:Person)
                    WHERE p.owner_id = $user_id OR p.user_id = $user_id
                    RETURN p
                """, user_id=user_id)
                
                for record in nodes_result:
                    node = dict(record["p"])
                    node["is_owner"] = True
                    for key in ['created_at', 'updated_at']:
                        if key in node and node[key]:
                            node[key] = str(node[key])
                    if node["id"] not in person_ids:
                        nodes.append(node)
                        person_ids.add(node["id"])  # ✅ ДОДАЄМО person_id
            
            # Отримати всі зв'язки між видимими персонами
            if person_ids:
                links_result = session.run("""
                    MATCH (a:Person)-[r]->(b:Person)
                    WHERE a.id IN $person_ids AND b.id IN $person_ids
                    AND type(r) IN ['PARENT_OF', 'CHILD_OF', 'SPOUSE', 'SIBLING']
                    RETURN a.id as source, b.id as target, type(r) as type, properties(r) as props
                """, person_ids=list(person_ids))
                
                links = []
                seen_links = set()
                
                for record in links_result:
                    link_key = f"{record['source']}-{record['target']}-{record['type']}"
                    if link_key not in seen_links:
                        seen_links.add(link_key)
                        links.append({
                            "source": record["source"],
                            "target": record["target"],
                            "type": record["type"],
                            "props": dict(record["props"]) if record["props"] else {}
                        })
            else:
                links = []
            
            return {"nodes": nodes, "links": links}
    
    def get_parents(self, person_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Отримати батьків особи"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (child:Person {id: $person_id, user_id: $user_id})
                      -[:CHILD_OF]->(parent:Person)
                RETURN parent
            """, person_id=person_id, user_id=user_id)
            return [dict(record["parent"]) for record in result]
    
    def get_children(self, person_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Отримати дітей особи"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (parent:Person {id: $person_id, user_id: $user_id})
                      -[:PARENT_OF]->(child:Person)
                RETURN child
                ORDER BY child.birth_year_approx
            """, person_id=person_id, user_id=user_id)
            return [dict(record["child"]) for record in result]
    
    def get_spouses(self, person_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Отримати подружжя особи (всіх, включно з розлученими)"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $person_id, user_id: $user_id})
                      -[r:SPOUSE]->(spouse:Person)
                RETURN spouse, 
                       r.status as status, 
                       r.marriage_order as order,
                       r.marriage_type as marriage_type,
                       r.marriage_year as marriage_year,
                       r.divorce_year as divorce_year
                ORDER BY r.marriage_order
            """, person_id=person_id, user_id=user_id)
            return [{
                **dict(record["spouse"]),
                "marriage_status": record["status"],
                "marriage_order": record["order"],
                "marriage_type": record["marriage_type"],
                "marriage_year": record["marriage_year"],
                "divorce_year": record["divorce_year"]
            } for record in result]
    
    def get_siblings(self, person_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Отримати братів/сестер особи"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $person_id, user_id: $user_id})
                      -[r:SIBLING]->(sibling:Person)
                RETURN sibling, r.type as sibling_type
            """, person_id=person_id, user_id=user_id)
            return [{
                **dict(record["sibling"]),
                "sibling_type": record["sibling_type"]
            } for record in result]
    
    # ==================== Автоматичні зв'язки ====================
    
    def auto_create_sibling_links(self, person_id: str, user_id: str):
        """
        Автоматично створити зв'язки SIBLING між дітьми спільних батьків.
        Визначає тип: full (обидва батьки спільні) або half (один батько).
        """
        with self.driver.session() as session:
            # Знайти всіх siblings через батьків
            session.run("""
                MATCH (p:Person {id: $person_id, user_id: $user_id})
                MATCH (p)-[:CHILD_OF]->(parent:Person)
                MATCH (parent)-[:PARENT_OF]->(sibling:Person)
                WHERE sibling.id <> p.id
                
                // Підрахувати скільки спільних батьків
                WITH p, sibling, collect(DISTINCT parent.id) as common_parents
                
                // Визначити тип: 2 спільних = full, 1 = half
                WITH p, sibling, 
                     CASE WHEN size(common_parents) >= 2 THEN 'full' ELSE 'half' END as stype
                
                // Створити зв'язок якщо ще немає
                MERGE (p)-[:SIBLING {type: stype}]->(sibling)
                MERGE (sibling)-[:SIBLING {type: stype}]->(p)
            """, person_id=person_id, user_id=user_id)
    
    # ==================== Guest Notes (Нотатки Гостя) ====================
    
    def add_guest_note(
        self,
        person_id: str,
        guest_user_id: str,
        note_blob: str
    ) -> Dict[str, Any]:
        """
        Додати приватну нотатку гостя до чужої персони.
        
        SECURITY:
        - Гість може мати СВОЇ нотатки до чужих персон
        - Ці нотатки НЕ видимі власнику
        - Зберігаються на зв'язку SHARED_WITH
        
        Args:
            person_id: ID персони
            guest_user_id: ID гостя
            note_blob: Зашифрована нотатка (ENC_...)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $guest_user_id})-[r:SHARED_WITH]->(p:Person {id: $person_id})
                SET r.guest_note_blob = $note_blob,
                    r.note_updated_at = datetime()
                RETURN r.guest_note_blob as note
            """,
                person_id=person_id,
                guest_user_id=guest_user_id,
                note_blob=note_blob
            )
            record = result.single()
            
            if record:
                return {"success": True, "note_blob": record["note"]}
            return {"success": False, "error": "Not a guest of this person"}
    
    def get_guest_note(self, person_id: str, guest_user_id: str) -> Optional[str]:
        """Отримати приватну нотатку гостя"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $guest_user_id})-[r:SHARED_WITH]->(p:Person {id: $person_id})
                RETURN r.guest_note_blob as note
            """, person_id=person_id, guest_user_id=guest_user_id)
            record = result.single()
            return record["note"] if record else None
    
    def share_note_with_owner(
        self,
        person_id: str,
        guest_user_id: str,
        note_blob: str
    ) -> Dict[str, Any]:
        """
        Поділитися нотаткою з власником (одностороння передача).
        
        Створює окремий вузол SharedNote, видимий власнику.
        """
        with self.driver.session() as session:
            import uuid
            note_id = f"note_{uuid.uuid4().hex[:12]}"
            
            result = session.run("""
                MATCH (guest:User {id: $guest_user_id})-[:SHARED_WITH]->(p:Person {id: $person_id})
                MATCH (owner:User)-[:OWNS]->(p)
                CREATE (n:SharedNote {
                    id: $note_id,
                    note_blob: $note_blob,
                    from_user_id: $guest_user_id,
                    created_at: datetime()
                })
                CREATE (p)-[:HAS_SHARED_NOTE]->(n)
                CREATE (guest)-[:WROTE_NOTE]->(n)
                RETURN n, owner.id as owner_id
            """,
                person_id=person_id,
                guest_user_id=guest_user_id,
                note_blob=note_blob,
                note_id=note_id
            )
            record = result.single()
            
            if record:
                return {
                    "success": True,
                    "note_id": note_id,
                    "shared_with": record["owner_id"]
                }
            return {"success": False, "error": "Cannot share note"}
    
    def get_shared_notes_for_person(self, person_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Отримати нотатки, якими поділилися гості (для власника)"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p:Person {id: $person_id})
                MATCH (p)-[:HAS_SHARED_NOTE]->(n:SharedNote)
                RETURN n.id as note_id, 
                       n.note_blob as note_blob, 
                       n.from_user_id as from_user,
                       n.created_at as created_at
                ORDER BY n.created_at DESC
            """, person_id=person_id, user_id=user_id)
            return [dict(record) for record in result]
    
    # ==================== Утиліти ====================
    
    def clear_user_data(self, user_id: str) -> int:
        """Видалити всі дані користувача (OWNS)"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p:Person)
                DETACH DELETE p
                RETURN count(p) as deleted
            """, user_id=user_id)
            record = result.single()
            return record["deleted"] if record else 0
    
    def clear_all(self) -> int:
        """Видалити ВСІ дані (для тестів)"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                DETACH DELETE n
                RETURN count(n) as deleted
            """)
            record = result.single()
            return record["deleted"] if record else 0
    
    def get_stats(self, user_id: str) -> Dict[str, int]:
        """Статистика дерева"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {user_id: $user_id})
                OPTIONAL MATCH (p)-[r]->()
                RETURN count(DISTINCT p) as persons, count(r) as relations
            """, user_id=user_id)
            record = result.single()
            return {
                "persons": record["persons"] if record else 0,
                "relations": record["relations"] if record else 0
            }


    # ==================== Sources (Джерела) ====================
    
    def create_source(
        self,
        source_id: str,
        user_id: str,
        title: str,
        archive_ref: Optional[str] = None,
        url: Optional[str] = None,
        confidence: str = "medium",
        notes: Optional[str] = None,
        from_rag: bool = False
    ) -> Dict[str, Any]:
        """
        Створити джерело інформації.
        
        Args:
            source_id: Унікальний ID джерела
            user_id: ID власника
            title: Назва документа/книги/архіву
            archive_ref: Шифр справи (ЦДІАК, ДАЛО тощо)
            url: Посилання (якщо онлайн)
            confidence: 'high' (документ), 'medium' (церковна книга), 'low' (усний переказ)
            notes: Нотатки до джерела
            from_rag: Чи знайдено через RAG (AI)
        
        Returns:
            Створене джерело
        """
        with self.driver.session() as session:
            result = session.run("""
                CREATE (s:Source {
                    id: $source_id,
                    user_id: $user_id,
                    title: $title,
                    archive_ref: $archive_ref,
                    url: $url,
                    confidence: $confidence,
                    notes: $notes,
                    from_rag: $from_rag,
                    created_at: datetime()
                })
                RETURN s
            """, 
                source_id=source_id,
                user_id=user_id,
                title=title,
                archive_ref=archive_ref,
                url=url,
                confidence=confidence,
                notes=notes,
                from_rag=from_rag
            )
            record = result.single()
            return dict(record["s"]) if record else None
    
    def get_source(self, source_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Отримати джерело за ID"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Source {id: $source_id, user_id: $user_id})
                RETURN s
            """, source_id=source_id, user_id=user_id)
            record = result.single()
            return dict(record["s"]) if record else None
    
    def link_source_to_person(
        self,
        person_id: str,
        source_id: str,
        user_id: str,
        evidence_type: str = "general"
    ) -> bool:
        """
        Прив'язати джерело до особи.
        
        (Person)-[:EVIDENCED_BY]->(Source)
        
        Args:
            person_id: ID особи
            source_id: ID джерела
            user_id: ID власника
            evidence_type: Тип доказу ('birth', 'death', 'marriage', 'general')
        
        Returns:
            True якщо успішно
        """
        with self.driver.session() as session:
            # Спочатку пробуємо через OWNS
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p:Person {id: $person_id})
                MATCH (s:Source {id: $source_id, user_id: $user_id})
                MERGE (p)-[r:EVIDENCED_BY {
                    evidence_type: $evidence_type,
                    linked_at: datetime()
                }]->(s)
                RETURN p, s
            """, person_id=person_id, source_id=source_id, user_id=user_id, evidence_type=evidence_type)
            record = result.single()
            
            if record:
                return True
            
            # Fallback для старого формату (owner_id/user_id в полі)
            result = session.run("""
                MATCH (p:Person {id: $person_id})
                WHERE p.owner_id = $user_id OR p.user_id = $user_id
                MATCH (s:Source {id: $source_id, user_id: $user_id})
                MERGE (p)-[r:EVIDENCED_BY {
                    evidence_type: $evidence_type,
                    linked_at: datetime()
                }]->(s)
                RETURN p, s
            """, person_id=person_id, source_id=source_id, user_id=user_id, evidence_type=evidence_type)
            record = result.single()
            return record is not None
    
    def get_sources_for_person(self, person_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Отримати всі джерела для особи"""
        with self.driver.session() as session:
            # Спробуємо через OWNS
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p:Person {id: $person_id})
                MATCH (p)-[r:EVIDENCED_BY]->(s:Source)
                RETURN s, r.evidence_type as evidence_type
            """, person_id=person_id, user_id=user_id)
            
            sources = [
                {**dict(record["s"]), "evidence_type": record["evidence_type"]}
                for record in result
            ]
            
            if sources:
                return sources
            
            # Fallback для старого формату
            result = session.run("""
                MATCH (p:Person {id: $person_id})-[r:EVIDENCED_BY]->(s:Source)
                WHERE p.owner_id = $user_id OR p.user_id = $user_id
                RETURN s, r.evidence_type as evidence_type
            """, person_id=person_id, user_id=user_id)
            return [
                {**dict(record["s"]), "evidence_type": record["evidence_type"]}
                for record in result
            ]
    
    def get_all_sources(self, user_id: str) -> List[Dict[str, Any]]:
        """Отримати всі джерела користувача"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Source {user_id: $user_id})
                RETURN s
                ORDER BY s.created_at DESC
            """, user_id=user_id)
            return [dict(record["s"]) for record in result]
    
    def delete_source(self, source_id: str, user_id: str) -> bool:
        """Видалити джерело"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Source {id: $source_id, user_id: $user_id})
                DETACH DELETE s
                RETURN count(s) as deleted
            """, source_id=source_id, user_id=user_id)
            record = result.single()
            return record["deleted"] > 0 if record else False
    
    # ==================== E2E Sharing (Zero-Knowledge) ====================
    
    def get_tree_for_sharing(self, user_id: str, exclude_private: bool = True) -> Dict[str, Any]:
        """
        Отримати дерево для sharing (без приватних даних).
        
        ZERO-KNOWLEDGE:
        - private_notes_blob НІКОЛИ не передається
        - marriage_type замінюється на generic 'married'/'divorced'
        - email, phone НЕ передаються
        
        Args:
            user_id: ID власника дерева
            exclude_private: Виключити приватні дані (default True)
        
        Returns:
            Дерево з обмеженими даними для sharing
        """
        with self.driver.session() as session:
            # Спробуємо через OWNS
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(p:Person)
                OPTIONAL MATCH (p)-[r]->(other:Person)
                WHERE (u)-[:OWNS]->(other)
                RETURN p, collect({rel: type(r), props: properties(r), target: other.id}) as relations
            """, user_id=user_id)
            
            records = list(result)
            
            # Fallback для старого формату
            if not records:
                result = session.run("""
                    MATCH (p:Person)
                    WHERE p.owner_id = $user_id OR p.user_id = $user_id
                    OPTIONAL MATCH (p)-[r]->(other:Person)
                    WHERE other.owner_id = $user_id OR other.user_id = $user_id
                    RETURN p, collect({rel: type(r), props: properties(r), target: other.id}) as relations
                """, user_id=user_id)
                records = list(result)
            
            nodes = []
            links = []
            seen_links = set()
            
            for record in records:
                person = dict(record["p"])
                
                # Видаляємо приватні дані для sharing
                if exclude_private:
                    person.pop("private_notes_blob", None)
                    person.pop("email", None)
                    person.pop("phone", None)
                
                nodes.append(person)
                
                for rel in record["relations"]:
                    if rel["target"]:
                        link_key = f"{person['id']}-{rel['rel']}-{rel['target']}"
                        if link_key not in seen_links:
                            link_data = {
                                "source": person["id"],
                                "target": rel["target"],
                                "type": rel["rel"]
                            }
                            
                            # Приховуємо деталі шлюбу для sharing
                            if exclude_private and rel["rel"] == "SPOUSE":
                                props = rel["props"] or {}
                                # Показуємо тільки статус, не тип
                                status = props.get("marriage_status", "married")
                                link_data["marriage_status"] = status
                                # НЕ передаємо marriage_type (civil/church)
                            else:
                                link_data.update(rel["props"] or {})
                            
                            links.append(link_data)
                            seen_links.add(link_key)
            
            return {"nodes": nodes, "links": links}


    # ==================== User Management (Crypto Keys) ====================
    
    def create_user(
        self,
        user_id: str,
        public_key: str,
        encrypted_private_key_blob: Optional[str] = None,
        recovery_salt: Optional[str] = None,
        email_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Створити користувача з криптографічними ключами.
        
        ZERO-KNOWLEDGE:
        - public_key: Зберігається відкрито (для sharing)
        - encrypted_private_key_blob: Зашифрований майстер-паролем (для recovery)
        - email_hash: Хеш email (для пошуку, не plaintext)
        
        Args:
            user_id: Унікальний ID користувача
            public_key: RSA публічний ключ (PEM або Base64)
            encrypted_private_key_blob: Зашифрований приватний ключ
            recovery_salt: Сіль для деривації ключа
            email_hash: SHA-256 хеш email
        """
        with self.driver.session() as session:
            result = session.run("""
                CREATE (u:User {
                    id: $user_id,
                    public_key: $public_key,
                    encrypted_private_key_blob: $encrypted_private_key_blob,
                    recovery_salt: $recovery_salt,
                    email_hash: $email_hash,
                    created_at: datetime()
                })
                RETURN u
            """,
                user_id=user_id,
                public_key=public_key,
                encrypted_private_key_blob=encrypted_private_key_blob,
                recovery_salt=recovery_salt,
                email_hash=email_hash
            )
            record = result.single()
            return dict(record["u"]) if record else None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Отримати користувача за ID"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})
                RETURN u
            """, user_id=user_id)
            record = result.single()
            return dict(record["u"]) if record else None
    
    def get_user_public_key(self, user_id: str) -> Optional[str]:
        """Отримати публічний ключ користувача (для sharing)"""
        user = self.get_user(user_id)
        return user.get("public_key") if user else None
    
    def get_user_recovery_data(self, user_id: str) -> Optional[Dict[str, str]]:
        """Отримати дані для відновлення (encrypted blob + salt)"""
        user = self.get_user(user_id)
        if not user:
            return None
        return {
            "encrypted_private_key_blob": user.get("encrypted_private_key_blob"),
            "recovery_salt": user.get("recovery_salt")
        }
    
    def update_user_keys(
        self,
        user_id: str,
        public_key: Optional[str] = None,
        encrypted_private_key_blob: Optional[str] = None,
        recovery_salt: Optional[str] = None
    ) -> bool:
        """Оновити ключі користувача"""
        updates = {}
        if public_key:
            updates["public_key"] = public_key
        if encrypted_private_key_blob:
            updates["encrypted_private_key_blob"] = encrypted_private_key_blob
        if recovery_salt:
            updates["recovery_salt"] = recovery_salt
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"u.{k} = ${k}" for k in updates.keys()])
        
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (u:User {{id: $user_id}})
                SET {set_clause}, u.updated_at = datetime()
                RETURN u
            """, user_id=user_id, **updates)
            return result.single() is not None
    
    # ==================== Sharing (QR Flow) ====================
    
    def create_invite(
        self,
        invite_id: str,
        owner_id: str,
        expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Створити запрошення для sharing (Крок 1: QR генерація).
        
        Args:
            invite_id: Унікальний ID запрошення (зашивається в QR)
            owner_id: ID власника дерева
            expires_at: Термін дії (ISO datetime)
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (owner:User {id: $owner_id})
                CREATE (i:Invite {
                    id: $invite_id,
                    owner_id: $owner_id,
                    status: 'pending',
                    created_at: datetime(),
                    expires_at: $expires_at
                })
                CREATE (owner)-[:CREATED_INVITE]->(i)
                RETURN i
            """,
                invite_id=invite_id,
                owner_id=owner_id,
                expires_at=expires_at
            )
            record = result.single()
            return dict(record["i"]) if record else None
    
    def accept_invite(
        self,
        invite_id: str,
        recipient_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Прийняти запрошення (Крок 2: Одержувач сканує QR).
        
        Повертає дані про запрошення та власника (включно з public_key).
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (i:Invite {id: $invite_id, status: 'pending'})
                MATCH (recipient:User {id: $recipient_id})
                SET i.recipient_id = $recipient_id,
                    i.status = 'accepted',
                    i.accepted_at = datetime()
                WITH i, recipient
                MATCH (owner:User {id: i.owner_id})
                RETURN i, owner.id as owner_id, owner.public_key as owner_public_key,
                       recipient.public_key as recipient_public_key
            """,
                invite_id=invite_id,
                recipient_id=recipient_id
            )
            record = result.single()
            if not record:
                return None
            return {
                "invite": dict(record["i"]),
                "owner_id": record["owner_id"],
                "owner_public_key": record["owner_public_key"],
                "recipient_public_key": record["recipient_public_key"]
            }
    
    def finalize_share(
        self,
        invite_id: str,
        owner_id: str,
        encrypted_tree_key: str
    ) -> bool:
        """
        Завершити sharing (Крок 3: Власник підтверджує).
        
        Створює зв'язок SHARED_WITH з зашифрованим Tree Key.
        
        Args:
            invite_id: ID запрошення
            owner_id: ID власника (перевірка)
            encrypted_tree_key: Tree Key, зашифрований публічним ключем одержувача
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (i:Invite {id: $invite_id, owner_id: $owner_id, status: 'accepted'})
                MATCH (owner:User {id: $owner_id})
                MATCH (recipient:User {id: i.recipient_id})
                SET i.status = 'completed',
                    i.completed_at = datetime()
                MERGE (owner)-[s:SHARED_WITH]->(recipient)
                SET s.encrypted_tree_key = $encrypted_tree_key,
                    s.created_at = datetime(),
                    s.invite_id = $invite_id
                RETURN s
            """,
                invite_id=invite_id,
                owner_id=owner_id,
                encrypted_tree_key=encrypted_tree_key
            )
            return result.single() is not None
    
    def get_shared_tree_key(
        self,
        owner_id: str,
        recipient_id: str
    ) -> Optional[str]:
        """
        Отримати зашифрований Tree Key (для одержувача).
        
        Returns:
            encrypted_tree_key або None
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (owner:User {id: $owner_id})-[s:SHARED_WITH]->(recipient:User {id: $recipient_id})
                RETURN s.encrypted_tree_key as encrypted_tree_key
            """,
                owner_id=owner_id,
                recipient_id=recipient_id
            )
            record = result.single()
            return record["encrypted_tree_key"] if record else None
    
    def get_shared_with_me(self, user_id: str) -> List[Dict[str, Any]]:
        """Отримати список дерев, до яких є доступ"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (owner:User)-[s:SHARED_WITH]->(me:User {id: $user_id})
                RETURN owner.id as owner_id, 
                       s.encrypted_tree_key as encrypted_tree_key,
                       s.created_at as shared_at
            """, user_id=user_id)
            return [dict(record) for record in result]
    
    def get_my_shares(self, user_id: str) -> List[Dict[str, Any]]:
        """Отримати список з ким я поділився"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (me:User {id: $user_id})-[s:SHARED_WITH]->(recipient:User)
                RETURN recipient.id as recipient_id,
                       s.created_at as shared_at
            """, user_id=user_id)
            return [dict(record) for record in result]
    
    def revoke_share(self, owner_id: str, recipient_id: str) -> bool:
        """Відкликати доступ"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (owner:User {id: $owner_id})-[s:SHARED_WITH]->(recipient:User {id: $recipient_id})
                DELETE s
                RETURN count(s) as deleted
            """,
                owner_id=owner_id,
                recipient_id=recipient_id
            )
            record = result.single()
            return record["deleted"] > 0 if record else False
    
    def get_pending_invites(self, owner_id: str) -> List[Dict[str, Any]]:
        """Отримати запрошення, що очікують підтвердження"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (owner:User {id: $owner_id})-[:CREATED_INVITE]->(i:Invite {status: 'accepted'})
                MATCH (recipient:User {id: i.recipient_id})
                RETURN i.id as invite_id,
                       recipient.id as recipient_id,
                       recipient.public_key as recipient_public_key,
                       i.accepted_at as accepted_at
            """, owner_id=owner_id)
            return [dict(record) for record in result]

    def create_relationship(
        self, 
        from_id: str, 
        to_id: str, 
        relation_type: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Створити зв'язок між особами (з PARTNER_PROJECT)
        
        Args:
            from_id: ID першої особи
            to_id: ID другої особи
            relation_type: Тип зв'язку (PARENT_OF, CHILD_OF, SPOUSE, SIBLING)
            metadata: Додаткові дані (marriage_date, divorce_date, etc.)
        
        Returns:
            bool: Успіх операції
        """
        # Нормалізуємо тип зв'язку
        relation_map = {
            "PARENT": "PARENT_OF",
            "CHILD": "CHILD_OF",
            "SPOUSE": "SPOUSE",
            "parent": "PARENT_OF",
            "child": "CHILD_OF",
            "spouse": "SPOUSE",
            "sibling": "SIBLING"
        }
        rel_type = relation_map.get(relation_type, relation_type.upper())
        
        query = f"""
        MATCH (from:Person {{id: $from_id}})
        MATCH (to:Person {{id: $to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        SET r.created_at = datetime(),
            r.updated_at = datetime()
        """
        
        # Додаємо метадані якщо є
        if metadata:
            for key, value in metadata.items():
                if key in ["marriage_date", "divorce_date", "is_adopted", "type"]:
                    query += f", r.{key} = ${key}"
        
        query += " RETURN r"
        
        params = {
            "from_id": from_id,
            "to_id": to_id
        }
        if metadata:
            for key, value in metadata.items():
                if key in ["marriage_date", "divorce_date", "is_adopted", "type"]:
                    params[key] = value
        
        try:
            with self.driver.session() as session:
                result = session.run(query, **params)
                return result.single() is not None
        except Exception as e:
            print(f"❌ Error creating relationship: {e}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance
_db_instance: Optional[Neo4jDB] = None

def get_db() -> Neo4jDB:
    """Отримати екземпляр бази даних"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Neo4jDB()
    return _db_instance
