"""
Enhanced PDF Processor для "Реабілітовані історією"
Підтримка: українська, російська, варіанти назв, всі професії
"""

import PyPDF2
import re
import json
from typing import List, Dict, Optional


class RehabilitationPDFProcessor:
    def __init__(self):
        # Розширений список професій (укр + рос)
        self.occupations = {
            # Сільське господарство
            'колгоспник': ['колгоспник', 'колхозник', 'колгоспниця', 'колхозница'],
            'селянин': ['селянин', 'крестьянин', 'селянка', 'одноосібник', 'единоличник'],
            'тракторист': ['тракторист', 'механізатор', 'механизатор'],
            'бригадир': ['бригадир', 'brigadir'],
            
            # Робітники
            'робітник': ['робітник', 'рабочий', 'робітниця', 'працівник', 'работница'],
            'слюсар': ['слюсар', 'слесарь'],
            'коваль': ['коваль', 'кузнец'],
            'столяр': ['столяр', 'stolar'],
            'тесля': ['тесля', 'плотник'],
            'швець': ['швець', 'сапожник'],
            
            # Медицина
            'лікар': ['лікар', 'врач', 'доктор', 'фельдшер', 'медик'],
            'медсестра': ['медсестра', 'медична сестра', 'медицинская сестра'],
            'фельдшер': ['фельдшер', 'feldsher'],
            
            # Освіта
            'вчитель': ['вчитель', 'учитель', 'педагог', 'викладач', 'преподаватель'],
            'директор': ['директор школи', 'директор', 'завідувач', 'заведующий'],
            
            # Культура
            'бібліотекар': ['бібліотекар', 'библиотекарь'],
            'завідувач клубу': ['завідувач клубу', 'зав. клубу', 'заведующий клубом'],
            'агітатор': ['агітатор', 'агитатор'],
            
            # Торгівля/Послуги
            'продавець': ['продавець', 'продавец'],
            'кухар': ['кухар', 'повар', 'кухарка'],
            'перукар': ['перукар', 'парикмахер'],
            
            # Адміністрація
            'голова': ['голова колгоспу', 'председатель', 'голова сільради', 'председатель колхоза'],
            'секретар': ['секретар', 'секретарь'],
            'рахівник': ['рахівник', 'счетовод', 'бухгалтер'],
            'економіст': ['економіст', 'экономист'],
            
            # Церква
            'священик': ['священик', 'священник', 'піп', 'поп', 'дяк'],
            'псаломщик': ['псаломщик', 'дяк'],
            
            # Військові
            'червоноармієць': ['червоноармієць', 'красноармеец'],
            'командир': ['командир', 'комбат'],
            
            # Транспорт
            'возний': ['возний', 'возчик', 'извозчик'],
            'шофер': ['шофер', 'водій', 'водитель'],
            
            # Інші
            'кустар': ['кустар', 'ремісник', 'ремесленник'],
            'музикант': ['музикант', 'музыкант'],
            'сторож': ['сторож', 'охоронець', 'охранник'],
            'безробітний': ['безробітний', 'безработный', 'не працював', 'не работал'],
            'домогосподарка': ['домогосподарка', 'домохозяйка', 'без професії', 'без профессии']
        }
        
        # Варіанти назв місць (укр/рос/старі назви)
        self.location_variants = {
            'Київ': ['Київ', 'Киев', 'Kyiv', 'Kiev'],
            'Баришівка': ['Баришівка', 'Барышевка', 'Baryshivka'],
            'Березань': ['Березань', 'Березань', 'Berezan'],
            'Бровари': ['Бровари', 'Броваpы', 'Brovary'],
            'Переяслав': ['Переяслав', 'Переяслав-Хмельницький', 'Переяславль']
        }

    def extract_records_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Головна функція витягування записів з PDF
        """
        print(f"📄 Обробляємо: {pdf_path}")
        records = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                full_text = ""
                
                # Збираємо весь текст
                for i, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        full_text += text + "\n"
                    except Exception as e:
                        print(f"⚠️ Помилка на сторінці {i}: {e}")
                        continue
                
                print(f"📝 Витягнуто {len(full_text)} символів")
                
                # Розбиваємо на записи
                entries = self._split_into_entries(full_text)
                print(f"📊 Знайдено {len(entries)} записів")
                
                # Парсимо кожен запис
                for entry in entries:
                    record = self._parse_entry(entry)
                    if record:
                        records.append(record)
                
                print(f"✅ Успішно оброблено {len(records)} записів")
                
        except Exception as e:
            print(f"❌ Помилка обробки PDF: {e}")
        
        return records

    def _split_into_entries(self, text: str) -> List[str]:
        """
        Розбиває текст на окремі записи
        Запис починається з ПРІЗВИЩА великими літерами
        """
        # Паттерн: ПРІЗВИЩЕ Ім'я По батькові
        # Українські та російські літери
        pattern = r'([А-ЯҐЄІЇЬА-Я\']+)\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я]+)\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я]+)'
        
        # Знаходимо всі входження
        matches = list(re.finditer(pattern, text))
        
        entries = []
        for i in range(len(matches)):
            start = matches[i].start()
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            entry_text = text[start:end].strip()
            
            # Фільтруємо занадто короткі записи
            if len(entry_text) > 100:
                entries.append(entry_text)
        
        return entries

    def _parse_entry(self, entry: str) -> Optional[Dict]:
        """
        Парсить один запис про репресовану особу
        """
        try:
            # Витягуємо ПІБ (перший рядок)
            name_match = re.match(
                r'([А-ЯҐЄІЇЬA-Я\']+)\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я]+)\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я]+)',
                entry
            )
            
            if not name_match:
                return None
            
            surname = name_match.group(1)
            first_name = name_match.group(2)
            patronymic = name_match.group(3)
            full_name = f"{first_name} {patronymic} {surname}"
            
            # Рік народження
            year_match = re.search(r'(\d{4})\s*рок[уа]?\s*народження', entry)
            birth_year = int(year_match.group(1)) if year_match else None
            
            # Місце народження (село/місто)
            location = self._extract_location(entry)
            
            # Район
            district_match = re.search(r'([А-ЯҐЄІЇA-Я][а-яґєіїьa-я]+ського)\s+район', entry)
            district = district_match.group(0) if district_match else None
            
            # Професія
            occupation = self._extract_occupation(entry)
            
            # Національність
            nationality_match = re.search(r'українець|українка|росіянин|росіянка|єврей|єврейка', entry, re.IGNORECASE)
            nationality = nationality_match.group(0) if nationality_match else None
            
            # Освіта
            education_match = re.search(
                r'освіта початкова|освіта середня|неписьменний|неписьменна|малописьменний|малописьменна',
                entry,
                re.IGNORECASE
            )
            education = education_match.group(0) if education_match else None
            
            # Формуємо запис
            record_id = f"rehab_{surname.lower()}_{birth_year}_{hash(entry) % 10000}"
            
            # Локація для відображення
            location_str = location
            if district:
                location_str = f"{location}, {district}"
            
            return {
                "id": record_id,
                "title": f"Реабілітовані історією - {full_name}",
                "content": entry[:500] + "..." if len(entry) > 500 else entry,
                "year": birth_year,
                "location": location_str,
                "metadata": {
                    "surnames": self._generate_surname_variants(surname),
                    "given_names": [first_name],
                    "person": full_name,
                    "occupation": occupation,
                    "nationality": nationality,
                    "education": education,
                    "source": "Реабілітовані історією",
                    "type": "репресований",
                    "location_variants": self._get_location_variants(location)
                }
            }
            
        except Exception as e:
            print(f"⚠️ Помилка парсингу запису: {e}")
            return None

    def _extract_location(self, text: str) -> str:
        """
        Витягує місце народження/проживання
        """
        # Шукаємо "с. Назва" або "м. Назва"
        patterns = [
            r'с\.\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я\-]+)',
            r'м\.\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я\-]+)',
            r'смт\s+([А-ЯҐЄІЇA-Я][а-яґєіїьa-я\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return "Невідомо"

    def _extract_occupation(self, text: str) -> Optional[str]:
        """
        Витягує професію з тексту
        """
        text_lower = text.lower()
        
        for occupation, keywords in self.occupations.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return occupation
        
        return None

    def _generate_surname_variants(self, surname: str) -> List[str]:
        """
        Генерує варіанти написання прізвища
        """
        variants = [surname]
        
        # Укр/Рос варіанти
        replacements = [
            ('І', 'И'), ('И', 'І'),
            ('Є', 'Е'), ('Е', 'Є'),
            ('Ї', 'И'), ('И', 'Ї'),
            ('ь', ''), ('ъ', ''),
        ]
        
        for old, new in replacements:
            if old in surname:
                variant = surname.replace(old, new)
                if variant not in variants:
                    variants.append(variant)
        
        return variants

    def _get_location_variants(self, location: str) -> List[str]:
        """
        Повертає варіанти написання локації
        """
        for main, variants in self.location_variants.items():
            if location in variants:
                return variants
        
        return [location]


# ============ UTILITY FUNCTIONS ============

def process_multiple_pdfs(pdf_paths: List[str], output_path: str = "data/archives_from_pdf.json"):
    """
    Обробляє кілька PDF файлів та зберігає результат
    """
    processor = RehabilitationPDFProcessor()
    all_records = []
    
    for pdf_path in pdf_paths:
        print(f"\n{'='*60}")
        records = processor.extract_records_from_pdf(pdf_path)
        all_records.extend(records)
        print(f"📊 Всього зараз: {len(all_records)} записів")
    
    # Зберігаємо
    output = {
        "archives": all_records,
        "total": len(all_records),
        "sources": pdf_paths
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Збережено {len(all_records)} записів у {output_path}")
    return all_records


def merge_with_existing(pdf_records_path: str, existing_path: str, output_path: str):
    """
    Об'єднує записи з PDF з існуючими JSON записами
    """
    # Завантажуємо PDF записи
    with open(pdf_records_path, 'r', encoding='utf-8') as f:
        pdf_data = json.load(f)
    
    # Завантажуємо існуючі
    with open(existing_path, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
    
    # Об'єднуємо
    all_archives = existing_data['archives'] + pdf_data['archives']
    
    result = {
        "archives": all_archives,
        "total": len(all_archives),
        "sources": {
            "manual": len(existing_data['archives']),
            "pdf": len(pdf_data['archives'])
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Об'єднано: {len(all_archives)} записів")
    print(f"   - Вручну: {len(existing_data['archives'])}")
    print(f"   - З PDF: {len(pdf_data['archives'])}")


# ============ MAIN ============

if __name__ == "__main__":
    print("🚀 PDF Processor для 'Реабілітовані історією'")
    print("="*60)
    
    # Шляхи до PDF
    pdf_files = [
        "data/pdfs/rehab_kyiv_1.pdf",
        "data/pdfs/rehab_kyiv_2.pdf",
        "data/pdfs/rehab_kyiv_3.pdf"
    ]
    
    # Обробляємо
    records = process_multiple_pdfs(pdf_files)
    
    # Статистика
    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Всього записів: {len(records)}")
    
    occupations = [r['metadata']['occupation'] for r in records if r['metadata'].get('occupation')]
    print(f"   З професією: {len(occupations)}")
    print(f"   Унікальних професій: {len(set(occupations))}")
    
    print("\n✅ Готово!")