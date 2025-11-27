"""
🌳 МОДУЛЬ B: Глибина та Складність Дерева (Graph Structure)
============================================================

Тести перевіряють коректність побудови зв'язків у Neo4j.
"""

import pytest
import time


class TestGenerations:
    """Тести глибини дерева"""
    
    @pytest.mark.critical
    @pytest.mark.integration
    def test_B1_five_generations_linear(self, db):
        """B-1: 5 поколінь (лінійне дерево)"""
        user_id = "test_user_gen"
        
        # Створюємо User
        db.create_user(user_id=user_id, public_key="pk")
        
        # Створюємо 5 поколінь
        generations = []
        for i in range(5):
            person_id = f"test_gen_{i}"
            person = db.create_person(
                person_id=person_id,
                user_id=user_id,
                name_blob=f"ENC_Gen_{i}",
                birth_year_approx=1900 + i * 25,
                gender="M" if i % 2 == 0 else "F"
            )
            generations.append(person_id)
            
            # Зв'язок з попереднім поколінням
            if i > 0:
                db.add_child(
                    parent_id=generations[i-1],
                    child_id=person_id,
                    user_id=user_id
                )
        
        # Перевірка: граф повинен мати 5 вузлів та 4 зв'язки
        tree = db.get_tree(user_id)
        
        assert len(tree["nodes"]) == 5, f"Expected 5 nodes, got {len(tree['nodes'])}"
        assert len(tree["links"]) >= 4, f"Expected at least 4 links, got {len(tree['links'])}"


class TestHalfSiblings:
    """Тести зведених братів/сестер"""
    
    @pytest.mark.critical
    @pytest.mark.integration
    def test_B2_half_siblings_different_mothers(self, db):
        """B-2: Half-siblings (зведені діти від різних матерів)"""
        user_id = "test_user_hs"
        db.create_user(user_id=user_id, public_key="pk")
        
        # Батько М1
        db.create_person(person_id="test_father", user_id=user_id, 
                        name_blob="ENC_Father", birth_year_approx=1950, gender="M")
        
        # Мати Ж1
        db.create_person(person_id="test_mother1", user_id=user_id,
                        name_blob="ENC_Mother1", birth_year_approx=1955, gender="F")
        
        # Мати Ж2 (друга дружина)
        db.create_person(person_id="test_mother2", user_id=user_id,
                        name_blob="ENC_Mother2", birth_year_approx=1960, gender="F")
        
        # Шлюб 1
        db.add_spouse(person1_id="test_father", person2_id="test_mother1",
                     user_id=user_id, status="divorced", divorce_year=1990)
        
        # Шлюб 2
        db.add_spouse(person1_id="test_father", person2_id="test_mother2",
                     user_id=user_id, status="married", marriage_year=1995)
        
        # Дитина Д1 від Ж1
        db.create_person(person_id="test_child1", user_id=user_id,
                        name_blob="ENC_Child1", birth_year_approx=1980, gender="M")
        db.add_child(parent_id="test_father", child_id="test_child1", user_id=user_id)
        db.add_child(parent_id="test_mother1", child_id="test_child1", user_id=user_id)
        
        # Дитина Д2 від Ж2
        db.create_person(person_id="test_child2", user_id=user_id,
                        name_blob="ENC_Child2", birth_year_approx=2000, gender="F")
        db.add_child(parent_id="test_father", child_id="test_child2", user_id=user_id)
        db.add_child(parent_id="test_mother2", child_id="test_child2", user_id=user_id)
        
        # Перевірка: Д1 і Д2 - half-siblings
        siblings = db.get_siblings("test_child1", user_id)
        
        assert len(siblings) >= 1, "Should have at least 1 sibling"
        
        # Знаходимо Д2
        child2_sibling = next((s for s in siblings if s["id"] == "test_child2"), None)
        assert child2_sibling is not None, "Child2 should be sibling of Child1"
        assert child2_sibling.get("sibling_type") == "half", "Should be half-sibling"
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_B4_full_siblings_same_parents(self, db):
        """B-4: Full siblings (рідні брати/сестри)"""
        user_id = "test_user_fs"
        db.create_user(user_id=user_id, public_key="pk")
        
        # Батьки
        db.create_person(person_id="test_father_fs", user_id=user_id,
                        name_blob="ENC_Father", birth_year_approx=1950, gender="M")
        db.create_person(person_id="test_mother_fs", user_id=user_id,
                        name_blob="ENC_Mother", birth_year_approx=1955, gender="F")
        
        # Шлюб
        db.add_spouse("test_father_fs", "test_mother_fs", user_id=user_id, status="married")
        
        # Дві дитини від тих самих батьків
        for i in range(2):
            child_id = f"test_child_fs_{i}"
            db.create_person(person_id=child_id, user_id=user_id,
                            name_blob=f"ENC_Child_{i}", birth_year_approx=1980+i*2)
            db.add_child("test_father_fs", child_id, user_id)
            db.add_child("test_mother_fs", child_id, user_id)
        
        # Перевірка: full siblings
        siblings = db.get_siblings("test_child_fs_0", user_id)
        
        assert len(siblings) >= 1
        sibling = siblings[0]
        assert sibling.get("sibling_type") == "full", "Should be full sibling"


class TestMultipleMarriages:
    """Тести множинних шлюбів"""
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_B3_three_sequential_marriages(self, db):
        """B-3: Жінка з 3 шлюбами поспіль"""
        user_id = "test_user_3m"
        db.create_user(user_id=user_id, public_key="pk")
        
        # Жінка
        db.create_person(person_id="test_woman", user_id=user_id,
                        name_blob="ENC_Woman", birth_year_approx=1950, gender="F")
        
        # 3 чоловіки
        husbands = []
        for i in range(3):
            husband_id = f"test_husband_{i}"
            db.create_person(person_id=husband_id, user_id=user_id,
                            name_blob=f"ENC_Husband_{i}", birth_year_approx=1945+i*5, gender="M")
            husbands.append(husband_id)
        
        # 3 шлюби (2 розлучення, 1 активний)
        db.add_spouse("test_woman", husbands[0], user_id, status="divorced", 
                     marriage_year=1970, divorce_year=1980)
        db.add_spouse("test_woman", husbands[1], user_id, status="divorced",
                     marriage_year=1985, divorce_year=1995)
        db.add_spouse("test_woman", husbands[2], user_id, status="married",
                     marriage_year=2000)
        
        # Перевірка: всі 3 шлюби в графі
        spouses = db.get_spouses("test_woman", user_id)
        
        assert len(spouses) == 3, f"Expected 3 spouses, got {len(spouses)}"
        
        # Перевірка що чоловіки не "склеїлись"
        spouse_ids = [s["id"] for s in spouses]
        assert len(set(spouse_ids)) == 3, "All husbands should be distinct"


class TestSpecialRelationships:
    """Спеціальні типи стосунків"""
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_B7_children_without_marriage(self, db):
        """B-7: Діти без шлюбу батьків"""
        user_id = "test_user_nm"
        db.create_user(user_id=user_id, public_key="pk")
        
        # Батьки (не одружені)
        db.create_person(person_id="test_unmarried_father", user_id=user_id,
                        name_blob="ENC_Father", birth_year_approx=1960, gender="M")
        db.create_person(person_id="test_unmarried_mother", user_id=user_id,
                        name_blob="ENC_Mother", birth_year_approx=1965, gender="F")
        
        # Дитина
        db.create_person(person_id="test_child_unmarried", user_id=user_id,
                        name_blob="ENC_Child", birth_year_approx=1990)
        
        # Додаємо PARENT_OF без SPOUSE
        db.add_child("test_unmarried_father", "test_child_unmarried", user_id)
        db.add_child("test_unmarried_mother", "test_child_unmarried", user_id)
        
        # Перевірка: дитина має 2 батьків
        parents = db.get_parents("test_child_unmarried", user_id)
        
        assert len(parents) == 2, "Child should have 2 parents"
        
        # Перевірка: батьки НЕ одружені
        spouses = db.get_spouses("test_unmarried_father", user_id)
        assert len(spouses) == 0, "Father should have no spouses"
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_B6_church_vs_civil_marriage(self, db):
        """B-6: Церковний vs цивільний шлюб"""
        user_id = "test_user_mt"
        db.create_user(user_id=user_id, public_key="pk")
        
        # Пара 1: цивільний шлюб
        db.create_person(person_id="test_civil_h", user_id=user_id,
                        name_blob="ENC_H1", gender="M")
        db.create_person(person_id="test_civil_w", user_id=user_id,
                        name_blob="ENC_W1", gender="F")
        db.add_spouse("test_civil_h", "test_civil_w", user_id, 
                     status="married", marriage_type="civil")
        
        # Пара 2: церковний шлюб
        db.create_person(person_id="test_church_h", user_id=user_id,
                        name_blob="ENC_H2", gender="M")
        db.create_person(person_id="test_church_w", user_id=user_id,
                        name_blob="ENC_W2", gender="F")
        db.add_spouse("test_church_h", "test_church_w", user_id,
                     status="married", marriage_type="church")
        
        # Перевірка типів
        spouse_civil = db.get_spouses("test_civil_h", user_id)
        spouse_church = db.get_spouses("test_church_h", user_id)
        
        assert spouse_civil[0].get("marriage_type") == "civil"
        assert spouse_church[0].get("marriage_type") == "church"


class TestPerformance:
    """Тести продуктивності"""
    
    @pytest.mark.performance
    @pytest.mark.integration
    def test_B10_large_tree_performance(self, db):
        """B-10: Граф з 50 вузлів завантажується за <200ms"""
        user_id = "test_user_perf"
        db.create_user(user_id=user_id, public_key="pk")
        
        # Створюємо 50 вузлів
        for i in range(50):
            db.create_person(
                person_id=f"test_perf_{i}",
                user_id=user_id,
                name_blob=f"ENC_Person_{i}",
                birth_year_approx=1900 + i
            )
        
        # Вимірюємо час завантаження
        start_time = time.time()
        tree = db.get_tree(user_id)
        end_time = time.time()
        
        load_time_ms = (end_time - start_time) * 1000
        
        assert len(tree["nodes"]) == 50, f"Expected 50 nodes, got {len(tree['nodes'])}"
        assert load_time_ms < 200, f"Load time {load_time_ms:.2f}ms exceeds 200ms limit"
        
        print(f"\n📊 Performance: 50 nodes loaded in {load_time_ms:.2f}ms")


class TestKovalenkoFamily:
    """Комплексний тест родини Коваленків"""
    
    @pytest.mark.critical
    @pytest.mark.integration
    def test_B9_kovalenko_family_complex(self, db, kovalenko_family_data):
        """B-9: Повна родина Коваленків (26 осіб, 4 покоління)"""
        user_id = "test_user_kov"
        db.create_user(user_id=user_id, public_key="pk")
        
        data = kovalenko_family_data
        
        # Створюємо Gen 1
        for p in data["gen1"]:
            db.create_person(
                person_id=f"test_kov_{p['id']}",
                user_id=user_id,
                name_blob=f"ENC_{p['name']}",
                birth_year_approx=p["birth"],
                gender=p["gender"]
            )
        
        # Створюємо Gen 2 з батьками
        for p in data["gen2"]:
            db.create_person(
                person_id=f"test_kov_{p['id']}",
                user_id=user_id,
                name_blob=f"ENC_{p['name']}",
                birth_year_approx=p["birth"],
                gender=p["gender"]
            )
            # Додаємо батьків
            for parent_id in p.get("parents", []):
                db.add_child(f"test_kov_{parent_id}", f"test_kov_{p['id']}", user_id)
        
        # Створюємо шлюби
        for m in data["marriages"]:
            db.add_spouse(
                f"test_kov_{m['person1']}", 
                f"test_kov_{m['person2']}",
                user_id=user_id,
                status=m["status"],
                marriage_year=m.get("year"),
                divorce_year=m.get("divorce_year")
            )
        
        # Перевірка структури
        tree = db.get_tree(user_id)
        
        assert len(tree["nodes"]) == 8, f"Gen1 + Gen2 = 8 persons"
        
        # Перевірка half-siblings
        # Андрій та Ігор мають спільного батька Петра, але різних матерів
        andriy_siblings = db.get_siblings("test_kov_andriy", user_id)
        
        # Має бути Марія (full), Ігор (half), Світлана (half)
        sibling_ids = [s["id"].replace("test_kov_", "") for s in andriy_siblings]
        
        assert "maria" in sibling_ids, "Maria should be sibling"
        assert "igor" in sibling_ids, "Igor should be half-sibling"
        
        print(f"\n✅ Kovalenko family created successfully!")
        print(f"   Nodes: {len(tree['nodes'])}")
        print(f"   Links: {len(tree['links'])}")

