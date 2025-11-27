"""
RAG Engine для пошуку в архівах
Використовує Sentence-BERT + евристичні правила
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from typing import List, Dict
from fuzzywuzzy import fuzz
import re


class RAGEngine:
    def __init__(self, archives_path: str = "data/archives.json"):
        """Ініціалізація RAG engine"""
        print("🔄 Завантаження Sentence-BERT моделі...")
        # Multilingual модель для української
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Завантаження архівів
        with open(archives_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.archives = data['archives']
        
        # Створення ембедінгів для всіх архівів
        print("🔄 Створення векторних ембедінгів...")
        self.archive_texts = [
            f"{arch['title']} {arch['content']} {' '.join(arch['metadata'].get('surnames', []))}"
            for arch in self.archives
        ]
        self.archive_embeddings = self.model.encode(self.archive_texts)
        print(f"✅ RAG готовий! Завантажено {len(self.archives)} архівних записів")
    
    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict]:
        """
        Головна функція пошуку
        
        Args:
            query: Запит користувача (напр. "мій прадід лікар Київ 1920-х")
            top_k: Кількість результатів
            threshold: Мінімальний поріг схожості (0-1)
        
        Returns:
            List[Dict]: Список знайдених записів з поясненням
        """
        print(f"\n🔍 Пошук: '{query}'")
        
        # 1. Векторний пошук (Sentence-BERT)
        query_embedding = self.model.encode([query])
        similarities = cosine_similarity(query_embedding, self.archive_embeddings)[0]
        
        # Топ-K кандидатів
        top_indices = np.argsort(similarities)[::-1][:top_k * 2]  # Беремо більше для фільтрації
        
        # 2. Додаємо евристичний scoring
        results = []
        for idx in top_indices:
            if similarities[idx] < threshold:
                continue
            
            archive = self.archives[idx]
            
            # Розраховуємо комплексний score
            semantic_score = float(similarities[idx])
            heuristic_score, explanation = self._calculate_heuristic_score(query, archive)
            
            final_score = (semantic_score * 0.6) + (heuristic_score * 0.4)
            
            results.append({
                "id": archive['id'],
                "title": archive['title'],
                "content": archive['content'],
                "year": archive['year'],
                "location": archive['location'],
                "semantic_score": round(semantic_score, 3),
                "heuristic_score": round(heuristic_score, 3),
                "confidence_score": round(final_score, 3),
                "explanation": explanation,
                "metadata": archive['metadata']
            })
        
        # Сортуємо за фінальним score
        results.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        return results[:top_k]
    
    def _calculate_heuristic_score(self, query: str, archive: Dict) -> tuple:
        """
        Евристичні правила для підвищення точності
        
        Returns:
            (score, explanation): Score 0-1 і текстове пояснення
        """
        query_lower = query.lower()
        score = 0.0
        explanations = []
        
        # 1. Перевірка прізвищ (найважливіше!)
        surnames_in_query = self._extract_surnames(query)
        archive_surnames = archive['metadata'].get('surnames', [])
        
        for query_surname in surnames_in_query:
            for archive_surname in archive_surnames:
                fuzzy_score = fuzz.ratio(query_surname.lower(), archive_surname.lower())
                if fuzzy_score > 80:  # Схожість >80%
                    score += 0.4
                    explanations.append(
                        f"Прізвище '{query_surname}' збігається з '{archive_surname}' "
                        f"(схожість {fuzzy_score}%)"
                    )
                    break
        
        # 2. Перевірка років
        years_in_query = self._extract_years(query)
        if years_in_query:
            archive_year = archive['year']
            for query_year in years_in_query:
                year_diff = abs(archive_year - query_year)
                if year_diff <= 5:
                    year_score = 0.3 * (1 - year_diff / 10)  # Чим ближче, тим краще
                    score += year_score
                    explanations.append(
                        f"Рік {archive_year} близький до запиту {query_year} (±{year_diff} років)"
                    )
        
        # 3. Перевірка професій (з синонімами)
        occupation_keywords = {
            'лікар': ['лікар', 'доктор', 'медик', 'терапевт'],
            'вчитель': ['вчитель', 'учитель', 'педагог', 'викладач'],
            'селянин': ['селянин', 'землероб', 'хлібороб'],
            'дяк': ['дяк', 'церковнослужитель']
        }
        
        for main_occupation, synonyms in occupation_keywords.items():
            if any(syn in query_lower for syn in synonyms):
                # Шукаємо в контенті та метаданих
                archive_text = (archive['content'] + ' ' + 
                               archive['metadata'].get('father_occupation', '') + ' ' +
                               archive['metadata'].get('mother_family', '')).lower()
                
                if any(syn in archive_text for syn in synonyms):
                    score += 0.2
                    explanations.append(
                        f"Професія '{main_occupation}' знайдена в документі"
                    )
                    break
        
        # 4. Перевірка локацій (з варіантами написання)
        location_variants = archive['metadata'].get('location_variants', [])
        for location in location_variants:
            if location.lower() in query_lower:
                score += 0.1
                explanations.append(f"Локація '{location}' збігається")
                break
        
        # Нормалізуємо score до 0-1
        score = min(score, 1.0)
        
        # Якщо немає пояснень, додаємо загальне
        if not explanations:
            explanations.append("Знайдено за семантичною схожістю контексту")
        
        return score, " • ".join(explanations)
    
    def _extract_surnames(self, text: str) -> List[str]:
        """Витягує прізвища з тексту (евристика: слова з великої літери)"""
        # Прості правила: слова з великої літери, довші за 3 символи
        words = text.split()
        surnames = []
        
        ukrainian_surnames_patterns = [
            r'\b[А-ЯҐЄІЇ][а-яґєії]{2,}(?:енко|enko|ук|юк|ський|цький|ич|ович|євич)\b',
            r'\b[А-ЯҐЄІЇ][а-яґєії]{3,}\b'
        ]
        
        for pattern in ukrainian_surnames_patterns:
            surnames.extend(re.findall(pattern, text))
        
        return list(set(surnames))  # Унікальні
    
    def _extract_years(self, text: str) -> List[int]:
        """Витягує роки з тексту"""
        # Шукаємо 4-значні числа, схожі на роки
        years = []
        
        # Паттерн для років
        year_patterns = [
            r'\b(19\d{2}|20\d{2})\b',  # Точні роки (1900-2099)
            r'\b(\d{2})-х\b'  # Десятиліття (20-х, 30-х)
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 4:
                    years.append(int(match))
                elif len(match) == 2:  # Десятиліття
                    # 20-х -> 1920
                    decade = int(match)
                    if decade < 30:
                        years.append(2000 + decade * 10)
                    else:
                        years.append(1900 + decade * 10)
        
        return years


# ============ ТЕСТИ ============
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТУВАННЯ RAG ENGINE")
    print("=" * 60)
    
    # Ініціалізація
    rag = RAGEngine()
    
    # Тест 1: Пошук по прізвищу + професія + місто
    print("\n\n📝 Тест 1: 'мій прадід лікар Коваленко Київ 1920-х'")
    results = rag.search("мій прадід лікар Коваленко Київ 1920-х", top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"🏆 Результат #{i} (Score: {result['confidence_score']})")
        print(f"📄 {result['title']}")
        print(f"📅 {result['year']} | 📍 {result['location']}")
        print(f"\n💡 Пояснення:")
        print(f"   {result['explanation']}")
        print(f"\n📖 Уривок:")
        print(f"   {result['content'][:200]}...")
    
    # Тест 2: Пошук по варіантах прізвища
    print("\n\n📝 Тест 2: 'Ковалєнко село Пирогів 1890'")
    results = rag.search("Ковалєнко село Пирогів 1890", top_k=2)
    
    for i, result in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"🏆 Результат #{i} (Score: {result['confidence_score']})")
        print(f"📄 {result['title']}")
        print(f"\n💡 {result['explanation']}")
    
    print("\n\n✅ Тести завершені!")