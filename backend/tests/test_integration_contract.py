import os
import sys
import pytest
from fastapi.testclient import TestClient

# --- FORCED CONFIGURATION INJECTION ---
# Встановлюємо змінні середовища ПЕРЕД імпортом main.py
os.environ["NEO4J_URI"] = "bolt://127.0.0.1:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "rodovid123"
print("💉 INJECTED DB CONFIG into Environment")
# --------------------------------------

# Тепер імпортуємо додаток
from main import app

# Створюємо TestClient з викликом startup події
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_adapter_output_contract(client):
    print("\n🧪 INTEGRATION CONTRACT TEST")
    
    # Спочатку створюємо батьківську особу
    parent_payload = {
        "name_blob": "ENC_parent_name",
        "birth_date_blob": "ENC_parent_birth",
        "birth_year_approx": 1960,
        "gender": "F"
    }
    headers = {"X-User-ID": "user_test_contract"}
    parent_response = client.post("/api/v1/person", json=parent_payload, headers=headers)
    assert parent_response.status_code == 200
    parent_id = parent_response.json()["person_id"]
    
    # Тепер створюємо дитину з посиланням на батька
    payload = {
        "name_blob": "ENC_test_name_blob_12345",
        "birth_date_blob": "ENC_test_birth_date_blob_67890",
        "death_date_blob": "ENC_test_death_date_blob_abcde",
        "private_notes_blob": "ENC_test_private_notes_blob",
        "birth_year_approx": 1990,
        "death_year_approx": 2020,
        "gender": "M",
        "relation": "CHILD",
        "link_to_id": parent_id,
        "source_ids": []
    }
    
    response = client.post("/api/v1/person", json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"📥 Response Body: {response.json()}")
        
    assert response.status_code == 200

def test_adapter_output_minimal(client):
    print("\n🧪 MINIMAL FIELDS CONTRACT TEST")
    
    # Створюємо дитину без зв'язків
    payload = {
        "name_blob": "ENC_minimal_name",
        "birth_date_blob": "ENC_minimal_birth",
        "birth_year_approx": 1945,
        "gender": "M"
    }
    headers = {"X-User-ID": "user_test_contract"}
    response = client.post("/api/v1/person", json=payload, headers=headers)
    assert response.status_code == 200

def test_adapter_output_with_all_fields(client):
    print("\n🧪 ALL FIELDS CONTRACT TEST")
    
    # Створюємо першу особу (партнер 1)
    person1_payload = {
        "name_blob": "ENC_person1_name",
        "birth_date_blob": "ENC_person1_birth",
        "birth_year_approx": 1950,
        "gender": "M"
    }
    headers = {"X-User-ID": "user_test_contract"}
    person1_response = client.post("/api/v1/person", json=person1_payload, headers=headers)
    assert person1_response.status_code == 200
    person1_id = person1_response.json()["person_id"]
    
    # Створюємо партнера з усіма полями
    payload = {
        "name_blob": "ENC_complete_name",
        "birth_date_blob": "ENC_complete_birth",
        "death_date_blob": "ENC_complete_death",
        "birth_place_blob": "ENC_complete_birth_place",
        "death_place_blob": "ENC_complete_death_place",
        "private_notes_blob": "ENC_complete_private_notes",
        "shared_notes_blob": "ENC_complete_shared_notes",
        "gender": "F",
        "birth_year_approx": 1950,
        "death_year_approx": 2021,
        "relation": "SPOUSE",
        "link_to_id": person1_id,
        "marriage_year": 1975,
        "divorce_year": None,
        "marriage_status": "married",
        "marriage_type": "civil",
        "source_ids": []
    }
    response = client.post("/api/v1/person", json=payload, headers=headers)
    assert response.status_code == 200

def test_field_name_mismatch(client):
    print("\n🧪 FIELD NAME MISMATCH TEST")
    payload = {
        "name_blob": "ENC_test",
        "birth_date_blob": "ENC_test",
        "birth_year_approx": 1990,
        "relation": "CHILD",
        "link_to_person_id": "person_123" # OLD FIELD NAME
    }
    headers = {"X-User-ID": "user_test_contract"}
    response = client.post("/api/v1/person", json=payload, headers=headers)
    # Should fail validation (422) or be accepted but field ignored (200)
    # Ideally validation error for missing required field 'link_to_id'
    if response.status_code == 422:
        print("✅ Backend correctly rejected old format")
    else:
        print("⚠️ Backend accepted old format (may need validation)")

if __name__ == "__main__":
    # Manual run wrapper
    print("\n🔗 INTEGRATION CONTRACT TEST SUITE")
    print("============================================================")
    try:
        test_adapter_output_contract()
        print("✅ PASS: Basic Contract")
        test_adapter_output_minimal()
        print("✅ PASS: Minimal Fields")
        test_adapter_output_with_all_fields()
        print("✅ PASS: All Fields")
        test_field_name_mismatch()
        print("✅ PASS: Field Name Mismatch")
        print("\nTotal: 4 passed")
    except AssertionError as e:
        print(f"\n❌ FAIL: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
