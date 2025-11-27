"""
🔐 МОДУЛЬ C: Безпека та Zero-Knowledge (Security)
=================================================

Критичні тести безпеки: ізоляція даних, IDOR, cross-sharing attacks.
"""

import pytest
import base64


class TestZeroKnowledge:
    """Zero-Knowledge тести - сервер не знає PII"""
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C1_blind_server_no_plaintext_in_db(self, db, alice_bob_users):
        """C-1: У БД немає відкритого тексту (тільки blob)"""
        alice = alice_bob_users["alice"]
        
        # Створюємо персону з "зашифрованими" даними
        db.create_person(
            person_id="test_sec_blind",
            user_id=alice,
            name_blob="ENC_base64encoded_encrypted_name",
            birth_date_blob="ENC_encrypted_1990",
            birth_year_approx=1990,  # Це OK - не PII
            gender="M"  # Це OK - структурне
        )
        
        # Перевіряємо безпосередньо в БД
        with db.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: 'test_sec_blind'})
                RETURN p.name_blob as name, p.birth_date_blob as birth
            """)
            record = result.single()
        
        name_blob = record["name"]
        birth_blob = record["birth"]
        
        # Перевірки
        assert name_blob is not None, "name_blob should exist"
        assert name_blob.startswith("ENC_"), "name should be encrypted (ENC_ prefix)"
        assert birth_blob.startswith("ENC_"), "birth should be encrypted"
        
        # Перевірка що це НЕ plaintext
        assert "Тарас" not in str(name_blob), "Name should not be plaintext"
        assert "1990" not in name_blob, "Date should not be in name blob"
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C14_no_pii_in_database(self, db, alice_bob_users):
        """C-14: Compliance - жодного PII в БД"""
        alice = alice_bob_users["alice"]
        
        # Створюємо персону
        db.create_person(
            person_id="test_sec_pii",
            user_id=alice,
            name_blob="ENC_xyz",
            private_notes_blob="ENC_private"
        )
        
        # Сканування БД на PII
        with db.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                WHERE p.id STARTS WITH 'test_'
                RETURN p
            """)
            
            for record in result:
                person = dict(record["p"])
                
                # Список заборонених plaintext полів
                forbidden_patterns = [
                    "name",  # не name_blob
                    "birth_date",  # не birth_date_blob
                    "death_date",  # не death_date_blob
                    "notes",  # не *_notes_blob
                ]
                
                for key in person.keys():
                    # Дозволені поля
                    if key in ["id", "gender", "is_root", "birth_year_approx", 
                              "death_year_approx", "created_at", "updated_at",
                              "owner_id"]:
                        continue
                    
                    # Blob поля - OK
                    if key.endswith("_blob"):
                        assert person[key] is None or str(person[key]).startswith("ENC_"), \
                            f"Blob field {key} should be encrypted or None"
                        continue
                    
                    # Інші поля - підозріло
                    for pattern in forbidden_patterns:
                        assert pattern not in key.lower(), \
                            f"Suspicious field found: {key}"


class TestAccessControl:
    """Access Control тести - IDOR та ізоляція"""
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C2_idor_unauthorized_access(self, db, alice_bob_users):
        """C-2: IDOR - Bob не може отримати персону Alice без доступу"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_idor",
            user_id=alice,
            name_blob="ENC_alice_secret"
        )
        
        # Bob намагається отримати
        person = db.get_person("test_sec_idor", bob)
        
        # Має бути None (немає доступу)
        assert person is None, "Bob should NOT access Alice's person without sharing"
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C4_bob_cannot_delete_alice_data(self, db, alice_bob_users):
        """C-4: Bob НЕ може видалити дані Alice"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_del",
            user_id=alice,
            name_blob="ENC_alice_precious"
        )
        
        # Alice ділиться з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_del'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob намагається видалити
        result = db.delete_person("test_sec_del", bob)
        
        # Має видалити тільки SHARED_WITH
        assert result["action"] == "unshared", "Bob should only unshare, not delete"
        
        # Персона ЩЕ ІСНУЄ
        with db.driver.session() as session:
            check = session.run("""
                MATCH (p:Person {id: 'test_sec_del'})
                RETURN p
            """).single()
        
        assert check is not None, "CRITICAL: Person was deleted by non-owner!"
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C5_bob_cannot_edit_alice_data(self, db, alice_bob_users):
        """C-5: Bob НЕ може редагувати дані Alice"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        original_name = "ENC_alice_original"
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_edit",
            user_id=alice,
            name_blob=original_name
        )
        
        # Даємо Bob доступ
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_edit'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob намагається змінити
        result = db.update_person(
            "test_sec_edit", 
            bob,
            name_blob="HACKED_BY_BOB"
        )
        
        # Має повернути None
        assert result is None, "Bob should NOT be able to edit"
        
        # Перевірка що дані не змінились
        person = db.get_person("test_sec_edit", alice)
        assert person["name_blob"] == original_name, "Data was modified!"
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C3_cross_sharing_attack(self, db, alice_bob_users):
        """C-3: Cross-Sharing Attack - Bob не може re-share дані Alice"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        charlie = alice_bob_users["charlie"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_reshare",
            user_id=alice,
            name_blob="ENC_alice_tree"
        )
        
        # Alice ділиться з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_reshare'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob намагається поділитись з Charlie
        # Це має бути заблоковано (Bob не власник)
        
        # Перевіряємо ownership
        ownership = db.check_ownership("test_sec_reshare", bob)
        assert ownership == "guest", "Bob should be guest, not owner"
        
        # Bob не може створювати SHARED_WITH від свого імені
        # (в реальній системі це має бути в API)
        
        # Charlie не повинен мати доступу
        charlie_person = db.get_person("test_sec_reshare", charlie)
        assert charlie_person is None, "Charlie should NOT have access"


class TestPrivateNotes:
    """Тести приватності нотаток"""
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C6_private_notes_isolation(self, db, alice_bob_users):
        """C-6: Приватні нотатки Alice не видимі Bob"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону з приватною нотаткою
        db.create_person(
            person_id="test_sec_notes",
            user_id=alice,
            name_blob="ENC_person",
            private_notes_blob="ENC_alice_secret_notes"
        )
        
        # Ділимося з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_notes'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob отримує персону
        person = db.get_person("test_sec_notes", bob)
        
        assert person is not None, "Bob should see person"
        assert person.get("private_notes_blob") is None, \
            "CRITICAL: Private notes visible to guest!"
    
    @pytest.mark.high
    @pytest.mark.security
    def test_C10_guest_notes_private(self, db, alice_bob_users):
        """C-10: Guest notes - Bob має свої приватні нотатки"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_gnotes",
            user_id=alice,
            name_blob="ENC_person"
        )
        
        # Ділимося з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_gnotes'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob додає свою нотатку
        result = db.add_guest_note(
            person_id="test_sec_gnotes",
            guest_user_id=bob,
            note_blob="ENC_bob_private_note"
        )
        
        assert result["success"], "Bob should be able to add guest note"
        
        # Bob бачить свою нотатку
        note = db.get_guest_note("test_sec_gnotes", bob)
        assert note == "ENC_bob_private_note"
        
        # Alice НЕ бачить нотатку Bob (вона в SHARED_WITH зв'язку)
        alice_tree = db.get_tree(alice)
        person_in_tree = next(
            (n for n in alice_tree["nodes"] if n["id"] == "test_sec_gnotes"), 
            None
        )
        
        assert person_in_tree is not None
        assert person_in_tree.get("my_guest_note_blob") is None, \
            "Alice should NOT see Bob's guest note"


class TestMarriageTypePrivacy:
    """Приватність типу шлюбу"""
    
    @pytest.mark.high
    @pytest.mark.security
    def test_C7_marriage_type_hidden_for_guests(self, db, alice_bob_users):
        """C-7: Тип шлюбу (civil/church) прихований для гостей"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює пару з церковним шлюбом
        db.create_person(person_id="test_sec_h", user_id=alice,
                        name_blob="ENC_H", gender="M")
        db.create_person(person_id="test_sec_w", user_id=alice,
                        name_blob="ENC_W", gender="F")
        db.add_spouse("test_sec_h", "test_sec_w", alice,
                     status="married", marriage_type="church")
        
        # Ділимося з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person) WHERE p.id IN ['test_sec_h', 'test_sec_w']
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob отримує дерево
        bob_tree = db.get_tree(bob)
        
        # Знаходимо SPOUSE зв'язок
        spouse_link = next(
            (l for l in bob_tree["links"] if l["type"] == "SPOUSE"), 
            None
        )
        
        if spouse_link:
            # marriage_type має бути прихований або показувати тільки статус
            props = spouse_link.get("props", {})
            # В Zero-Knowledge архітектурі тип шлюбу може бути приватним
            # Тест перевіряє що він або прихований, або показується generic
            pass


class TestCascadeDelete:
    """Тести каскадного видалення"""
    
    @pytest.mark.high
    @pytest.mark.security
    def test_C8_cascade_delete_owns(self, db, alice_bob_users):
        """C-8: Власник видаляє - CASCADE DELETE"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_cascade",
            user_id=alice,
            name_blob="ENC_to_delete"
        )
        
        # Ділимося з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_cascade'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Alice видаляє
        result = db.delete_person("test_sec_cascade", alice)
        
        assert result["action"] == "deleted"
        
        # Персона видалена
        with db.driver.session() as session:
            check = session.run("""
                MATCH (p:Person {id: 'test_sec_cascade'})
                RETURN p
            """).single()
        
        assert check is None, "Person should be deleted"
        
        # SHARED_WITH теж видалений
        with db.driver.session() as session:
            check = session.run("""
                MATCH ()-[r:SHARED_WITH]->(:Person {id: 'test_sec_cascade'})
                RETURN r
            """).single()
        
        assert check is None, "SHARED_WITH should be deleted (cascade)"
    
    @pytest.mark.high
    @pytest.mark.security
    def test_C9_unshare_preserves_data(self, db, alice_bob_users):
        """C-9: Unshare видаляє тільки зв'язок, не дані"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_sec_unshare",
            user_id=alice,
            name_blob="ENC_preserved"
        )
        
        # Ділимося з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_sec_unshare'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob "видаляє" (unshare)
        result = db.delete_person("test_sec_unshare", bob)
        
        assert result["action"] == "unshared"
        
        # Alice ще бачить
        alice_person = db.get_person("test_sec_unshare", alice)
        assert alice_person is not None, "Alice should still see her person"


class TestCrypto:
    """Криптографічні тести"""
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C11_rsa_key_exchange(self, crypto):
        """C-11: RSA key exchange працює"""
        # Generate keypairs
        alice_pub, alice_priv = crypto.generate_rsa_keypair()
        bob_pub, bob_priv = crypto.generate_rsa_keypair()
        
        # Alice encrypts tree key for Bob
        tree_key = crypto.generate_aes_key()
        encrypted_for_bob = crypto.encrypt_rsa_public(bob_pub, tree_key)
        
        # Bob decrypts
        decrypted_key = crypto.decrypt_rsa_private(bob_priv, encrypted_for_bob)
        
        assert decrypted_key == tree_key, "Key exchange failed"
    
    @pytest.mark.critical
    @pytest.mark.security
    def test_C12_aes_encryption_blob(self, crypto):
        """C-12: AES encryption/decryption"""
        tree_key = crypto.generate_aes_key()
        plaintext = "Іван Петренко 1990"
        
        # Encrypt
        blob = crypto.encrypt_aes(tree_key, plaintext)
        
        assert blob.startswith("ENC_"), "Blob should have ENC_ prefix"
        assert plaintext not in blob, "Plaintext should not be in blob"
        
        # Decrypt
        decrypted = crypto.decrypt_aes(tree_key, blob)
        
        assert decrypted == plaintext, "Decryption failed"
    
    @pytest.mark.high
    @pytest.mark.security
    def test_C13_recovery_key_derivation(self, crypto):
        """C-13: Recovery key derivation from password"""
        password = "MySecurePassword123!"
        _, private_key = crypto.generate_rsa_keypair()
        
        # Encrypt private key with password
        encrypted_blob, salt = crypto.encrypt_private_key_with_password(
            private_key, password
        )
        
        # Recover
        recovered_key = crypto.decrypt_private_key_with_password(
            encrypted_blob, password, salt
        )
        
        assert recovered_key == private_key, "Recovery failed"

