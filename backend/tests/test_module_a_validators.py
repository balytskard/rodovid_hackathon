"""
🧪 МОДУЛЬ A: Валідація Логіки (Validators & TimeResolver)
==========================================================

Тести перевіряють, що система відхиляє фізично неможливі дані.
"""

import pytest
from validators import FamilyValidator, ValidationResult
from utils.time_resolver import TimeResolver


class TestTemporalParadoxes:
    """Темпоральні парадокси (T1-T6)"""
    
    @pytest.mark.critical
    def test_T1_death_before_birth(self, validator):
        """T1: Смерть раніше народження"""
        result = validator.validate_death_before_birth(
            birth_year=1990,
            death_year=1980
        )
        
        assert not result.is_valid
        assert result.error_code == "T1_DEATH_BEFORE_BIRTH"
        assert "раніше" in result.message.lower() or "before" in result.message.lower()
    
    @pytest.mark.critical
    def test_T2_parent_younger_than_child(self, validator):
        """T2: Батько молодший за дитину"""
        result = validator.validate_parent_age(
            parent_birth_year=2000,
            child_birth_year=1990
        )
        
        assert not result.is_valid
        assert result.error_code == "T2_PARENT_YOUNGER"
    
    @pytest.mark.critical
    def test_T3_mother_ghost(self, validator):
        """T3: Дитина народилась після смерті матері"""
        result = validator.validate_mother_alive_at_birth(
            mother_death_year=1990,
            child_birth_year=1995
        )
        
        assert not result.is_valid
        assert result.error_code == "T3_MOTHER_GHOST"
    
    @pytest.mark.high
    def test_T4_father_ghost_warning(self, validator):
        """T4: Дитина народилась через 2+ роки після смерті батька"""
        result = validator.validate_father_alive_at_conception(
            father_death_year=1990,
            child_birth_year=1995
        )
        
        # Може бути warning або error залежно від strict_mode
        assert not result.is_valid or result.warning
    
    @pytest.mark.critical
    def test_T5_child_marriage(self, validator):
        """T5: Шлюб у занадто молодому віці"""
        result = validator.validate_marriage_age(
            birth_year=1990,
            marriage_year=1995
        )
        
        assert not result.is_valid
        assert result.error_code == "T5_CHILD_MARRIAGE"
    
    @pytest.mark.critical
    def test_T6_divorce_before_marriage(self, validator):
        """T6: Розлучення раніше шлюбу"""
        result = validator.validate_divorce_after_marriage(
            marriage_year=2000,
            divorce_year=1995
        )
        
        assert not result.is_valid
        assert result.error_code == "T6_DIVORCE_BEFORE_MARRIAGE"


class TestTimeResolver:
    """Гнучкий парсинг дат (TimeResolver)"""
    
    @pytest.mark.high
    def test_exact_year(self, time_resolver):
        """Точний рік: 1990 → 1990"""
        result = time_resolver.resolve_year("1990")
        assert result == 1990
    
    @pytest.mark.high
    def test_approximate_tilde(self, time_resolver):
        """Приблизний рік: ~1900 → 1900"""
        result = time_resolver.resolve_year("~1900")
        assert result == 1900
    
    @pytest.mark.high
    def test_approximate_circa(self, time_resolver):
        """Приблизний рік: c. 1900 → 1900"""
        result = time_resolver.resolve_year("c. 1900")
        assert result == 1900
    
    @pytest.mark.high
    def test_range(self, time_resolver):
        """Діапазон: 1910..1920 → 1915 (середина)"""
        result = time_resolver.resolve_year("1910..1920")
        assert result == 1915
    
    @pytest.mark.high
    def test_unknown_question_mark(self, time_resolver):
        """Невідомо: ? → None"""
        result = time_resolver.resolve_year("?")
        assert result is None
    
    @pytest.mark.high
    def test_unknown_text(self, time_resolver):
        """Невідомо: unknown → None"""
        result = time_resolver.resolve_year("unknown")
        assert result is None
    
    @pytest.mark.high
    def test_full_date(self, time_resolver):
        """Повна дата: 15.03.1990 → 1990"""
        result = time_resolver.resolve_year("15.03.1990")
        assert result == 1990
    
    @pytest.mark.high
    def test_validation_skipped_for_unknown(self, validator):
        """Валідація пропускається для невідомих дат"""
        # Якщо birth_year None - валідація має бути пропущена
        result = validator.validate_death_before_birth(
            birth_year=None,
            death_year=1990
        )
        
        # Має бути valid (пропущено) або спеціальний статус
        assert result.is_valid or result.skipped


class TestTopologicalParadoxes:
    """Топологічні парадокси (C1-C4)"""
    
    @pytest.mark.critical
    def test_C1_self_marriage(self, validator):
        """C1: Шлюб сам на собі"""
        result = validator.validate_no_self_relation(
            person1_id="person_1",
            person2_id="person_1",
            relation_type="SPOUSE"
        )
        
        assert not result.is_valid
        assert result.error_code == "C1_SELF_RELATION"
    
    @pytest.mark.critical
    def test_C2_self_parent(self, validator):
        """C2: Сам собі батько"""
        result = validator.validate_no_self_relation(
            person1_id="person_1",
            person2_id="person_1",
            relation_type="PARENT_OF"
        )
        
        assert not result.is_valid


class TestBiologicalLimits:
    """Біологічні обмеження (B1-B4)"""
    
    @pytest.mark.high
    def test_B1_parent_too_young(self, validator):
        """B1: Батько занадто молодий (< 10 років)"""
        result = validator.validate_parent_age(
            parent_birth_year=1990,
            child_birth_year=1995
        )
        
        assert not result.is_valid
        assert result.error_code in ["B1_PARENT_TOO_YOUNG", "T2_PARENT_YOUNGER"]
    
    @pytest.mark.medium
    def test_B2_mother_too_old(self, validator):
        """B2: Мати занадто стара (> 55-60)"""
        result = validator.validate_mother_age(
            mother_birth_year=1920,
            child_birth_year=2000
        )
        
        # Warning або error
        assert not result.is_valid or result.warning


class TestPolygamy:
    """Полігамія (M1-M2)"""
    
    @pytest.mark.critical
    def test_M1_active_polygamy(self, validator, db):
        """M1: Два активних шлюби"""
        # Створюємо особу з активним шлюбом
        # Перевіряємо що другий активний шлюб заборонений
        
        # Це потребує db fixture для перевірки в графі
        result = validator.validate_no_active_marriage(
            person_id="test_person_1",
            existing_marriages=[
                {"status": "married", "partner_id": "spouse_1"}
            ]
        )
        
        assert not result.is_valid
        assert result.error_code == "M1_POLYGAMY"


class TestEdgeCases:
    """Граничні випадки"""
    
    @pytest.mark.high
    def test_valid_person_passes_all(self, validator):
        """Валідна особа проходить всі перевірки"""
        result = validator.validate_person_data(
            birth_year=1990,
            death_year=2050,
            gender="M"
        )
        
        assert result.is_valid
    
    @pytest.mark.medium
    def test_empty_data_handled_gracefully(self, validator):
        """Порожні дані обробляються коректно"""
        result = validator.validate_person_data(
            birth_year=None,
            death_year=None,
            gender=None
        )
        
        # Не повинно впасти з exception
        assert result is not None
    
    @pytest.mark.high
    def test_historical_dates_accepted(self, validator):
        """Історичні дати приймаються"""
        result = validator.validate_person_data(
            birth_year=1800,
            death_year=1880,
            gender="F"
        )
        
        assert result.is_valid
    
    @pytest.mark.medium
    def test_future_dates_warning(self, validator):
        """Майбутні дати викликають warning"""
        result = validator.validate_person_data(
            birth_year=2030,
            death_year=None,
            gender="M"
        )
        
        # Може бути warning або error
        assert result.warning or not result.is_valid

