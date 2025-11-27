"""
Pytest конфігурація та фікстури
================================
"""

import sys
import os
import pytest

# Додаємо backend до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j_db import get_db, Neo4jDB
from validators import FamilyValidator
from utils.time_resolver import TimeResolver, get_resolver
from utils.crypto import CryptoModule, get_crypto


# ==================== Markers ====================

def pytest_configure(config):
    """Реєстрація кастомних маркерів"""
    config.addinivalue_line("markers", "critical: Critical priority tests")
    config.addinivalue_line("markers", "high: High priority tests")
    config.addinivalue_line("markers", "medium: Medium priority tests")
    config.addinivalue_line("markers", "low: Low priority tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "unit: Unit tests")


# ==================== Фікстури ====================

@pytest.fixture(scope="session")
def db():
    """Neo4j database connection"""
    database = get_db()
    yield database


@pytest.fixture(scope="session")
def validator():
    """Family validator instance"""
    return FamilyValidator(strict_mode=True)


@pytest.fixture(scope="session")
def time_resolver():
    """TimeResolver instance"""
    return get_resolver()


@pytest.fixture(scope="session")
def crypto():
    """Crypto module instance"""
    return get_crypto()


@pytest.fixture(autouse=True)
def clean_test_data(db):
    """Автоматичне очищення тестових даних"""
    yield
    # Cleanup після кожного тесту
    with db.driver.session() as session:
        session.run("MATCH (n) WHERE n.id STARTS WITH 'test_' DETACH DELETE n")
        session.run("MATCH (u:User) WHERE u.id STARTS WITH 'test_' DETACH DELETE u")


@pytest.fixture
def alice_bob_users(db):
    """Фікстура для тестів Alice vs Bob"""
    # Cleanup
    with db.driver.session() as session:
        session.run("MATCH (u:User) WHERE u.id IN ['test_alice', 'test_bob', 'test_charlie'] DETACH DELETE u")
    
    # Create users
    db.create_user(user_id="test_alice", public_key="alice_pk")
    db.create_user(user_id="test_bob", public_key="bob_pk")
    db.create_user(user_id="test_charlie", public_key="charlie_pk")
    
    yield {
        "alice": "test_alice",
        "bob": "test_bob",
        "charlie": "test_charlie"
    }
    
    # Cleanup
    with db.driver.session() as session:
        session.run("MATCH (u:User) WHERE u.id IN ['test_alice', 'test_bob', 'test_charlie'] DETACH DELETE u")


@pytest.fixture
def sample_person_data():
    """Зразкові дані особи"""
    return {
        "name_blob": "ENC_test_name_blob",
        "birth_date_blob": "ENC_test_birth",
        "birth_year_approx": 1990,
        "gender": "M"
    }


@pytest.fixture
def kovalenko_family_data():
    """Дані родини Коваленків для складних тестів"""
    return {
        "gen1": [
            {"id": "petro", "name": "Петро Коваленко", "birth": 1930, "gender": "M"},
            {"id": "olena", "name": "Олена Захарова", "birth": 1932, "gender": "F"},
            {"id": "galyna", "name": "Галина Рибак", "birth": 1940, "gender": "F"},
            {"id": "dmytro", "name": "Дмитро Кравченко", "birth": 1935, "gender": "M"},
        ],
        "gen2": [
            {"id": "andriy", "name": "Андрій Коваленко", "birth": 1955, "gender": "M", "parents": ["petro", "olena"]},
            {"id": "maria", "name": "Марія Коваленко", "birth": 1958, "gender": "F", "parents": ["petro", "olena"]},
            {"id": "igor", "name": "Ігор Коваленко", "birth": 1980, "gender": "M", "parents": ["petro", "galyna"]},
            {"id": "svitlana", "name": "Світлана Кравченко", "birth": 1982, "gender": "F", "parents": ["dmytro", "olena"]},
        ],
        "marriages": [
            {"person1": "petro", "person2": "olena", "year": 1950, "status": "divorced", "divorce_year": 1975},
            {"person1": "petro", "person2": "galyna", "year": 1978, "status": "married"},
            {"person1": "olena", "person2": "dmytro", "year": 1980, "status": "married"},
        ]
    }

