"""
📜 МОДУЛЬ E: Робота з Архівами (RAG/Sources)
=============================================

Тести прив'язки архівних документів до персон.
"""

import pytest


class TestSourceCRUD:
    """CRUD операції для Sources"""
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_E1_create_source(self, db, alice_bob_users):
        """E-1: Створення Source"""
        alice = alice_bob_users["alice"]
        
        source = db.create_source(
            source_id="test_src_1",
            user_id=alice,
            title="Метрична книга 1897",
            archive_ref="ЦДІАК, Ф.127, Оп.1, Спр.123",
            url="https://archives.gov.ua/...",
            confidence="high"
        )
        
        assert source is not None
        assert source["id"] == "test_src_1"
        assert source["title"] == "Метрична книга 1897"
        assert source["confidence"] == "high"
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_E2_link_source_to_person(self, db, alice_bob_users):
        """E-2: Прив'язка Source до Person"""
        alice = alice_bob_users["alice"]
        
        # Створюємо Person
        db.create_person(
            person_id="test_person_src",
            user_id=alice,
            name_blob="ENC_person_with_source"
        )
        
        # Створюємо Source
        db.create_source(
            source_id="test_src_2",
            user_id=alice,
            title="Запис про народження"
        )
        
        # Зв'язуємо
        result = db.link_source_to_person(
            source_id="test_src_2",
            person_id="test_person_src",
            user_id=alice
        )
        
        assert result["success"]
        
        # Перевіряємо зв'язок
        sources = db.get_sources_for_person("test_person_src", alice)
        
        assert len(sources) >= 1
        assert any(s["id"] == "test_src_2" for s in sources)
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_E3_multiple_sources_per_person(self, db, alice_bob_users):
        """E-3: Кілька Sources для одної Person"""
        alice = alice_bob_users["alice"]
        
        # Створюємо Person
        db.create_person(
            person_id="test_person_multi_src",
            user_id=alice,
            name_blob="ENC_person"
        )
        
        # Створюємо 3 Sources
        for i in range(3):
            db.create_source(
                source_id=f"test_multi_src_{i}",
                user_id=alice,
                title=f"Документ #{i}"
            )
            db.link_source_to_person(
                source_id=f"test_multi_src_{i}",
                person_id="test_person_multi_src",
                user_id=alice
            )
        
        # Перевіряємо
        sources = db.get_sources_for_person("test_person_multi_src", alice)
        
        assert len(sources) == 3


class TestSourceLifecycle:
    """Тести життєвого циклу Sources"""
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_E4_orphan_source_after_person_deleted(self, db, alice_bob_users):
        """E-4: Source залишається після видалення Person"""
        alice = alice_bob_users["alice"]
        
        # Створюємо Person
        db.create_person(
            person_id="test_orphan_person",
            user_id=alice,
            name_blob="ENC_to_delete"
        )
        
        # Створюємо Source та зв'язуємо
        db.create_source(
            source_id="test_orphan_src",
            user_id=alice,
            title="Архівний документ"
        )
        db.link_source_to_person(
            source_id="test_orphan_src",
            person_id="test_orphan_person",
            user_id=alice
        )
        
        # Видаляємо Person
        db.delete_person("test_orphan_person", alice)
        
        # Source має залишитися!
        source = db.get_source("test_orphan_src", alice)
        
        assert source is not None, "Source should survive person deletion"
        assert source["title"] == "Архівний документ"
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_E5_source_confidence_levels(self, db, alice_bob_users):
        """E-5: Рівні впевненості Source"""
        alice = alice_bob_users["alice"]
        
        confidence_levels = ["high", "medium", "low", "unknown"]
        
        for i, level in enumerate(confidence_levels):
            source = db.create_source(
                source_id=f"test_conf_{i}",
                user_id=alice,
                title=f"Document {level}",
                confidence=level
            )
            
            assert source["confidence"] == level
        
        # Перевірка всіх
        all_sources = db.get_all_sources(alice)
        
        created_sources = [s for s in all_sources if s["id"].startswith("test_conf_")]
        assert len(created_sources) == 4


class TestSourceMetadata:
    """Тести метаданих Sources"""
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_E7_from_rag_flag(self, db, alice_bob_users):
        """E-7: Прапорець from_rag для RAG-знайдених джерел"""
        alice = alice_bob_users["alice"]
        
        # Source знайдений через RAG
        source = db.create_source(
            source_id="test_rag_src",
            user_id=alice,
            title="RAG найдений запис",
            from_rag=True
        )
        
        assert source.get("from_rag") == True
        
        # Source доданий вручну
        source2 = db.create_source(
            source_id="test_manual_src",
            user_id=alice,
            title="Ручний запис",
            from_rag=False
        )
        
        assert source2.get("from_rag") == False or source2.get("from_rag") is None
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_E8_sources_list(self, db, alice_bob_users):
        """E-8: Отримання списку всіх Sources"""
        alice = alice_bob_users["alice"]
        
        # Створюємо кілька Sources
        for i in range(5):
            db.create_source(
                source_id=f"test_list_src_{i}",
                user_id=alice,
                title=f"Source #{i}"
            )
        
        # Отримуємо список
        all_sources = db.get_all_sources(alice)
        
        created = [s for s in all_sources if s["id"].startswith("test_list_src_")]
        assert len(created) == 5


class TestSourcePrivacy:
    """Тести приватності Sources"""
    
    @pytest.mark.high
    @pytest.mark.security
    def test_source_isolation_between_users(self, db, alice_bob_users):
        """Sources одного користувача не видимі іншому"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює Source
        db.create_source(
            source_id="test_private_src",
            user_id=alice,
            title="Alice's private source"
        )
        
        # Bob не бачить
        bob_sources = db.get_all_sources(bob)
        
        alice_sources = [s for s in bob_sources if s["id"] == "test_private_src"]
        assert len(alice_sources) == 0, "Bob should NOT see Alice's sources"

