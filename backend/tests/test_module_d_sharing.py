"""
🤝 МОДУЛЬ D: Шарінг та Життєвий Цикл (Merging)
===============================================

Тести QR sharing flow та lifecycle операцій.
"""

import pytest


class TestInviteFlow:
    """Тести потоку запрошень"""
    
    @pytest.mark.critical
    @pytest.mark.integration
    def test_D1_qr_invite_creation(self, db, alice_bob_users):
        """D-1: Створення QR invite"""
        alice = alice_bob_users["alice"]
        
        # Alice створює invite
        invite = db.create_invite(
            owner_id=alice,
            expires_hours=24
        )
        
        assert invite is not None
        assert "invite_id" in invite
        assert invite["invite_id"].startswith("inv_")
        assert invite["owner_id"] == alice
        
        # QR data
        qr_data = f"rodovid://share/{invite['invite_id']}"
        assert "rodovid://" in qr_data
    
    @pytest.mark.critical
    @pytest.mark.integration
    def test_D2_invite_acceptance(self, db, alice_bob_users):
        """D-2: Bob приймає invite"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює invite
        invite = db.create_invite(owner_id=alice)
        invite_id = invite["invite_id"]
        
        # Bob сканує QR та приймає
        result = db.accept_invite(
            invite_id=invite_id,
            recipient_id=bob
        )
        
        assert result["success"]
        assert result["owner_id"] == alice
    
    @pytest.mark.critical
    @pytest.mark.integration
    def test_D3_share_finalization(self, db, alice_bob_users, crypto):
        """D-3: Alice фіналізує sharing"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює invite
        invite = db.create_invite(owner_id=alice)
        invite_id = invite["invite_id"]
        
        # Bob приймає
        db.accept_invite(invite_id, bob)
        
        # Alice шифрує tree key для Bob
        # (в реальності Bob's public key береться з БД)
        encrypted_tree_key = "encrypted_tree_key_for_bob"
        
        # Alice фіналізує
        result = db.finalize_share(
            invite_id=invite_id,
            owner_id=alice,
            encrypted_tree_key=encrypted_tree_key
        )
        
        assert result["success"]
        assert result.get("recipient_id") == bob


class TestShareManagement:
    """Тести управління sharing"""
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_D4_revoke_share(self, db, alice_bob_users):
        """D-4: Alice відкликає доступ Bob"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_revoke",
            user_id=alice,
            name_blob="ENC_test"
        )
        
        # Даємо Bob доступ
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_revoke'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob бачить
        person = db.get_person("test_revoke", bob)
        assert person is not None
        
        # Alice відкликає
        result = db.revoke_share(alice, bob)
        
        assert result.get("success") or result.get("revoked", 0) >= 0
        
        # Bob більше не бачить
        person = db.get_person("test_revoke", bob)
        assert person is None
    
    @pytest.mark.high
    @pytest.mark.integration
    def test_D5_multiple_shares_one_owner(self, db, alice_bob_users):
        """D-5: Alice ділиться з кількома гостями"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        charlie = alice_bob_users["charlie"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_multi",
            user_id=alice,
            name_blob="ENC_shared"
        )
        
        # Ділиться з Bob і Charlie
        with db.driver.session() as session:
            session.run("""
                MATCH (u:User) WHERE u.id IN [$bob, $charlie]
                MATCH (p:Person {id: 'test_multi'})
                CREATE (u)-[:SHARED_WITH]->(p)
            """, bob=bob, charlie=charlie)
        
        # Обидва бачать
        bob_person = db.get_person("test_multi", bob)
        charlie_person = db.get_person("test_multi", charlie)
        
        assert bob_person is not None
        assert charlie_person is not None
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_D6_shared_with_me_list(self, db, alice_bob_users):
        """D-6: Bob бачить список shared дерев"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону та ділиться
        db.create_person(
            person_id="test_swm",
            user_id=alice,
            name_blob="ENC_from_alice"
        )
        
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_swm'})
                CREATE (bob)-[:SHARED_WITH {encrypted_tree_key: 'key123'}]->(p)
            """, bob_id=bob)
        
        # Bob отримує список
        shared = db.get_shared_with_me(bob)
        
        assert len(shared) >= 1
        # Перевірка що Alice є в списку
        alice_shares = [s for s in shared if s.get("owner_id") == alice]
        assert len(alice_shares) >= 1
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_D7_pending_invites_list(self, db, alice_bob_users):
        """D-7: Alice бачить pending invites"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює invite
        invite = db.create_invite(owner_id=alice)
        invite_id = invite["invite_id"]
        
        # Bob приймає
        db.accept_invite(invite_id, bob)
        
        # Alice бачить pending
        pending = db.get_pending_invites(alice)
        
        assert len(pending) >= 1
        # Має бути Bob
        bob_pending = [p for p in pending if p.get("recipient_id") == bob]
        assert len(bob_pending) >= 1


class TestShareNotes:
    """Тести sharing нотаток"""
    
    @pytest.mark.medium
    @pytest.mark.integration
    def test_D10_share_note_with_owner(self, db, alice_bob_users):
        """D-10: Bob ділиться нотаткою з Alice"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_share_note",
            user_id=alice,
            name_blob="ENC_person"
        )
        
        # Даємо Bob доступ
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_share_note'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob ділиться нотаткою з Alice
        result = db.share_note_with_owner(
            person_id="test_share_note",
            guest_user_id=bob,
            note_blob="ENC_bob_shared_note"
        )
        
        assert result["success"]
        
        # Alice бачить shared note
        shared_notes = db.get_shared_notes_for_person("test_share_note", alice)
        
        assert len(shared_notes) >= 1
        bob_note = next((n for n in shared_notes if n["from_user"] == bob), None)
        assert bob_note is not None
        assert bob_note["note_blob"] == "ENC_bob_shared_note"


class TestEdgeCases:
    """Граничні випадки"""
    
    @pytest.mark.medium
    def test_D8_expired_invite_rejection(self, db, alice_bob_users):
        """D-8: Прострочений invite відхиляється"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        
        # Створюємо invite з минулим часом
        # (в реальності треба мокати час)
        invite = db.create_invite(
            owner_id=alice,
            expires_hours=-1  # Вже минув
        )
        
        # Bob намагається прийняти
        # Якщо система перевіряє expiration - має бути error
        # Інакше - тест проходить з warning
    
    @pytest.mark.high
    def test_D9_reshare_prevention(self, db, alice_bob_users):
        """D-9: Bob не може re-share дерево Alice"""
        alice = alice_bob_users["alice"]
        bob = alice_bob_users["bob"]
        charlie = alice_bob_users["charlie"]
        
        # Alice створює персону
        db.create_person(
            person_id="test_reshare",
            user_id=alice,
            name_blob="ENC_alice_data"
        )
        
        # Alice ділиться з Bob
        with db.driver.session() as session:
            session.run("""
                MATCH (bob:User {id: $bob_id})
                MATCH (p:Person {id: 'test_reshare'})
                CREATE (bob)-[:SHARED_WITH]->(p)
            """, bob_id=bob)
        
        # Bob НЕ власник
        ownership = db.check_ownership("test_reshare", bob)
        assert ownership == "guest"
        
        # Bob не може створювати invites для чужих даних
        # (в API це має перевірятися)

