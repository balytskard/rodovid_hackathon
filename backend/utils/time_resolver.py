"""
TimeResolver - Парсер гнучких історичних дат
============================================

Проблема: Історичні дати часто неточні ("біля 1900", "1910-1920").
Рішення: Парсимо текст і повертаємо числове значення для валідації.

Формати:
- "1990" → 1990
- "1990-05-20" → 1990
- "c. 1900", "~1900", "≈1900" → 1900
- "1910..1920", "1910-1920" → 1915 (середнє)
- "?", "unknown", "", None → None (пропустити валідацію)
"""

import re
from typing import Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class ResolvedDate:
    """Результат парсингу дати"""
    year: Optional[int]           # Рік для валідації (або None)
    original: str                 # Оригінальний текст
    is_approximate: bool          # Чи приблизна дата
    range_start: Optional[int]    # Початок діапазону (якщо є)
    range_end: Optional[int]      # Кінець діапазону (якщо є)
    confidence: str               # "exact", "approximate", "range", "unknown"


class TimeResolver:
    """
    Парсер гнучких історичних дат.
    
    Використання:
        resolver = TimeResolver()
        result = resolver.resolve("~1900")
        print(result.year)  # 1900
        print(result.is_approximate)  # True
    """
    
    # Регулярні вирази
    PATTERNS = {
        # Точна дата: 1990, 1990-05-20, 20.05.1990
        'exact': r'^(\d{4})(?:[-./]\d{1,2}[-./]\d{1,2})?$',
        
        # Європейський формат: 20.05.1990, 20/05/1990
        'exact_euro': r'^\d{1,2}[-./]\d{1,2}[-./](\d{4})$',
        
        # Приблизна: c. 1900, ~1900, ≈1900, circa 1900, близько 1900
        'approximate': r'^(?:c\.?\s*|~|≈|circa\s+|близько\s+|приблизно\s+|біля\s+)(\d{4})$',
        
        # Діапазон: 1910..1920, 1910-1920, 1910—1920
        'range': r'^(\d{4})(?:\.{2}|[-–—])(\d{4})$',
        
        # Невідомо: ?, unknown, невідомо, empty
        'unknown': r'^(?:\?|unknown|невідомо|empty|не\s*відомо|\s*)$',
        
        # Тільки рік в тексті: "народився 1900 року"
        'year_in_text': r'(\d{4})',
    }
    
    def __init__(self):
        # Компілюємо регулярки
        self._patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }
    
    def resolve(self, date_input: Union[str, int, None]) -> ResolvedDate:
        """
        Розпарсити дату.
        
        Args:
            date_input: Рік (int), текстова дата (str), або None
            
        Returns:
            ResolvedDate з інтерпретованим роком
        """
        # None або порожнє
        if date_input is None:
            return ResolvedDate(
                year=None,
                original="",
                is_approximate=False,
                range_start=None,
                range_end=None,
                confidence="unknown"
            )
        
        # Якщо вже число - повертаємо
        if isinstance(date_input, int):
            return ResolvedDate(
                year=date_input,
                original=str(date_input),
                is_approximate=False,
                range_start=None,
                range_end=None,
                confidence="exact"
            )
        
        # Текст
        text = str(date_input).strip()
        
        if not text:
            return ResolvedDate(
                year=None,
                original="",
                is_approximate=False,
                range_start=None,
                range_end=None,
                confidence="unknown"
            )
        
        # Перевіряємо невідоме
        if self._patterns['unknown'].match(text):
            return ResolvedDate(
                year=None,
                original=text,
                is_approximate=False,
                range_start=None,
                range_end=None,
                confidence="unknown"
            )
        
        # Перевіряємо точну дату
        match = self._patterns['exact'].match(text)
        if match:
            year = int(match.group(1))
            return ResolvedDate(
                year=year,
                original=text,
                is_approximate=False,
                range_start=None,
                range_end=None,
                confidence="exact"
            )
        
        # Перевіряємо європейський формат (DD.MM.YYYY)
        match = self._patterns['exact_euro'].match(text)
        if match:
            year = int(match.group(1))
            return ResolvedDate(
                year=year,
                original=text,
                is_approximate=False,
                range_start=None,
                range_end=None,
                confidence="exact"
            )
        
        # Перевіряємо приблизну
        match = self._patterns['approximate'].match(text)
        if match:
            year = int(match.group(1))
            return ResolvedDate(
                year=year,
                original=text,
                is_approximate=True,
                range_start=None,
                range_end=None,
                confidence="approximate"
            )
        
        # Перевіряємо діапазон
        match = self._patterns['range'].match(text)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            middle = (start + end) // 2
            return ResolvedDate(
                year=middle,
                original=text,
                is_approximate=True,
                range_start=start,
                range_end=end,
                confidence="range"
            )
        
        # Спробуємо знайти рік в тексті
        match = self._patterns['year_in_text'].search(text)
        if match:
            year = int(match.group(1))
            # Перевірка що це схоже на рік (1000-2100)
            if 1000 <= year <= 2100:
                return ResolvedDate(
                    year=year,
                    original=text,
                    is_approximate=True,
                    range_start=None,
                    range_end=None,
                    confidence="approximate"
                )
        
        # Не вдалося розпарсити
        return ResolvedDate(
            year=None,
            original=text,
            is_approximate=False,
            range_start=None,
            range_end=None,
            confidence="unknown"
        )
    
    def resolve_year(self, date_input: Union[str, int, None]) -> Optional[int]:
        """
        Швидкий метод - повертає тільки рік або None.
        Для використання у валідаторах.
        """
        return self.resolve(date_input).year
    
    def can_validate(self, date_input: Union[str, int, None]) -> bool:
        """
        Чи можна валідувати цю дату?
        True якщо вдалося отримати числовий рік.
        """
        return self.resolve(date_input).year is not None


# Singleton instance
_resolver: Optional[TimeResolver] = None

def get_resolver() -> TimeResolver:
    """Отримати екземпляр TimeResolver"""
    global _resolver
    if _resolver is None:
        _resolver = TimeResolver()
    return _resolver


def resolve_year(date_input: Union[str, int, None]) -> Optional[int]:
    """Швидка функція для отримання року"""
    return get_resolver().resolve_year(date_input)


def resolve_date(date_input: Union[str, int, None]) -> ResolvedDate:
    """Швидка функція для повного парсингу"""
    return get_resolver().resolve(date_input)

