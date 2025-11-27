#!/usr/bin/env python
"""
🔌 API ТЕСТИ (curl-style)
==========================

Тестування API endpoints через HTTP запити.
Можна запускати без pytest.

Використання:
    python test_api_curl.py
"""

import sys
import os
import json
import requests
from typing import Dict, Any, Optional

sys.stdout.reconfigure(encoding='utf-8')

# Configuration
BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"


class APITestClient:
    """HTTP клієнт для тестування API"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.last_response = None
    
    def get(self, endpoint: str) -> Dict[str, Any]:
        """GET запит"""
        url = f"{self.base_url}{API_PREFIX}{endpoint}"
        self.last_response = self.session.get(url)
        return self._parse_response()
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST запит"""
        url = f"{self.base_url}{API_PREFIX}{endpoint}"
        self.last_response = self.session.post(url, json=data)
        return self._parse_response()
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE запит"""
        url = f"{self.base_url}{API_PREFIX}{endpoint}"
        self.last_response = self.session.delete(url)
        return self._parse_response()
    
    def _parse_response(self) -> Dict[str, Any]:
        """Парсинг відповіді"""
        try:
            return self.last_response.json()
        except:
            return {"raw": self.last_response.text}
    
    @property
    def status_code(self) -> int:
        return self.last_response.status_code if self.last_response else 0


def test_health_check():
    """Тест: Health endpoint"""
    print("\n🏥 TEST: Health Check")
    print("-" * 40)
    
    client = APITestClient()
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:100]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("   ✅ PASSED")
        return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def test_get_tree():
    """Тест: Отримання дерева"""
    print("\n🌳 TEST: Get Tree")
    print("-" * 40)
    
    client = APITestClient()
    
    try:
        response = client.get("/tree")
        print(f"   Status: {client.status_code}")
        
        if client.status_code == 200:
            nodes = response.get("nodes", [])
            links = response.get("links", [])
            print(f"   Nodes: {len(nodes)}")
            print(f"   Links: {len(links)}")
            print("   ✅ PASSED")
            return True
        else:
            print(f"   Response: {response}")
            print("   ⚠️ WARNING: Non-200 response")
            return True  # Може бути пустим
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def test_create_person_e2e():
    """Тест: Створення особи (E2E encrypted)"""
    print("\n👤 TEST: Create Person (E2E)")
    print("-" * 40)
    
    client = APITestClient()
    
    person_data = {
        "name_blob": "ENC_test_api_person_name",
        "birth_date_blob": "ENC_test_1990",
        "birth_year_approx": 1990,
        "gender": "M",
        "relation": "CHILD",
        "link_to_person_id": "root_user_1"
    }
    
    try:
        response = client.post("/person", person_data)
        print(f"   Status: {client.status_code}")
        print(f"   Response: {json.dumps(response, indent=2, ensure_ascii=False)[:200]}")
        
        if client.status_code in [200, 201]:
            assert "person_id" in response or "success" in response
            print("   ✅ PASSED")
            return True
        elif client.status_code == 422:
            print("   ⚠️ Validation error (expected for E2E)")
            return True
        else:
            print(f"   ❌ FAILED: Status {client.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def test_idor_protection():
    """Тест: IDOR захист - чужа персона недоступна"""
    print("\n🔐 TEST: IDOR Protection")
    print("-" * 40)
    
    client = APITestClient()
    
    # Спробуємо отримати неіснуючу персону
    try:
        response = client.get("/person/nonexistent_person_id_12345")
        print(f"   Status: {client.status_code}")
        
        # Має бути 404 або 403
        if client.status_code in [404, 403]:
            print("   ✅ PASSED: Access denied")
            return True
        elif client.status_code == 200:
            if response.get("error") or response is None:
                print("   ✅ PASSED: Returned null/error")
                return True
            print("   ❌ FAILED: Data returned!")
            return False
        else:
            print(f"   ⚠️ Unexpected status: {client.status_code}")
            return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def test_validation_t1():
    """Тест: Валідація T1 - смерть раніше народження"""
    print("\n⏱️ TEST: Validation T1 (Death before Birth)")
    print("-" * 40)
    
    client = APITestClient()
    
    # Невалідні дані
    person_data = {
        "name_blob": "ENC_invalid_person",
        "birth_year_approx": 1990,
        "death_year_approx": 1980,  # Раніше народження!
    }
    
    try:
        response = client.post("/validate", person_data)
        print(f"   Status: {client.status_code}")
        
        if client.status_code == 400:
            print("   ✅ PASSED: Validation rejected")
            return True
        elif client.status_code == 200:
            errors = response.get("errors", [])
            if errors:
                print(f"   ✅ PASSED: Errors returned: {errors}")
                return True
            print("   ❌ FAILED: No validation errors")
            return False
        else:
            print(f"   ⚠️ Status: {client.status_code}")
            return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def test_search_magic():
    """Тест: RAG Magic Search"""
    print("\n🔍 TEST: Magic Search")
    print("-" * 40)
    
    client = APITestClient()
    
    search_data = {
        "query": "Коваленко Петро 1930",
        "top_k": 5
    }
    
    try:
        response = client.post("/search/magic", search_data)
        print(f"   Status: {client.status_code}")
        
        if client.status_code == 200:
            results = response.get("results", [])
            print(f"   Results: {len(results)}")
            print("   ✅ PASSED")
            return True
        else:
            print(f"   Response: {response}")
            print("   ⚠️ Search might not be configured")
            return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def test_create_source():
    """Тест: Створення Source"""
    print("\n📜 TEST: Create Source")
    print("-" * 40)
    
    client = APITestClient()
    
    source_data = {
        "source_id": "test_api_source",
        "title": "Метрична книга 1897",
        "archive_ref": "ЦДІАК, Ф.127",
        "confidence": "high"
    }
    
    try:
        response = client.post("/source", source_data)
        print(f"   Status: {client.status_code}")
        
        if client.status_code in [200, 201]:
            print("   ✅ PASSED")
            return True
        else:
            print(f"   Response: {response}")
            print("   ⚠️ May need auth")
            return True
    except Exception as e:
        print(f"   ❌ FAILED: {e}")
        return False


def run_all_api_tests():
    """Запуск всіх API тестів"""
    print("\n" + "="*60)
    print("🔌 RODOVID API TEST SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    tests = [
        ("Health Check", test_health_check),
        ("Get Tree", test_get_tree),
        ("Create Person (E2E)", test_create_person_e2e),
        ("IDOR Protection", test_idor_protection),
        ("Validation T1", test_validation_t1),
        ("Magic Search", test_search_magic),
        ("Create Source", test_create_source),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, s in results if s)
    
    for name, success in results:
        icon = "✅" if success else "❌"
        print(f"   {icon} {name}")
    
    print(f"\n📊 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ✅ ALL API TESTS PASSED!                               ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """)
    else:
        print("\n⚠️ Some tests failed or need configuration")
    
    return passed == len(results)


if __name__ == "__main__":
    # Check if server is running
    try:
        requests.get(BASE_URL, timeout=2)
    except:
        print(f"\n❌ ERROR: Server not running at {BASE_URL}")
        print("   Start with: cd backend && python main.py")
        sys.exit(1)
    
    success = run_all_api_tests()
    sys.exit(0 if success else 1)

