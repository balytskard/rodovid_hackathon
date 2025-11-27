"""
Валідатори для Родовід
======================
Перевірка логічних помилок перед записом в БД.

Категорії:
- T: Темпоральні парадокси (час)
- C: Топологічні парадокси (цикли)
- Z: Логіка станів (живий/мертвий)
- B: Біологічні обмеження
- M: Багатоженство і дублікати

Особливість: Підтримка гнучких історичних дат через TimeResolver.
"""

from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# TimeResolver для гнучких дат
from utils.time_resolver import resolve_year, resolve_date, ResolvedDate


class ValidationLevel(str, Enum):
    ERROR = "error"      # Блокує операцію
    WARNING = "warning"  # Попередження, але дозволяє
    SKIPPED = "skipped"  # Пропущено (невідома дата)


@dataclass
class ValidationResult:
    """Результат валідації"""
    valid: bool
    level: ValidationLevel
    code: str
    message: str
    
    def __str__(self):
        if self.level == ValidationLevel.SKIPPED:
            return f"⏭️ [{self.code}] {self.message}"
        icon = "❌" if self.level == ValidationLevel.ERROR else "⚠️"
        return f"{icon} [{self.code}] {self.message}"


class FamilyValidator:
    """
    Валідатор для родинних зв'язків з підтримкою гнучких дат.
    
    Використання:
        validator = FamilyValidator()
        results = validator.validate_person(person_data)
        results = validator.validate_relationship(parent, child, "PARENT_OF")
    
    Гнучкі дати:
        - "1990" → 1990 (точна)
        - "~1900", "c. 1900" → 1900 (приблизна)
        - "1910..1920" → 1915 (середнє)
        - "?", "unknown" → None (пропустити валідацію)
    """
    
    # Константи
    MIN_MARRIAGE_AGE = 14           # Мінімальний вік для шлюбу (історичні дані)
    MIN_PARENT_AGE = 10             # Мінімальний вік батьківства
    MAX_MOTHER_AGE = 60             # Максимальний вік матері при народженні
    MAX_FATHER_POSTHUMOUS = 1       # Років після смерті батька (9 міс ≈ 1 рік)
    MAX_HUMAN_AGE = 130             # Максимальний реалістичний вік
    CURRENT_YEAR = datetime.now().year
    
    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: True = errors блокують, False = тільки warnings
        """
        self.strict_mode = strict_mode
    
    def _resolve(self, date_input: Union[str, int, None]) -> Optional[int]:
        """Розпарсити дату через TimeResolver"""
        return resolve_year(date_input)
    
    # ==================== T: Темпоральні парадокси ====================
    
    def validate_birth_death(
        self, 
        birth_year: Union[str, int, None], 
        death_year: Union[str, int, None]
    ) -> List[ValidationResult]:
        """T1: Перевірка дат народження/смерті (з підтримкою гнучких дат)"""
        results = []
        
        # Розпарсити дати
        birth = self._resolve(birth_year)
        death = self._resolve(death_year)
        
        # Якщо обидві дати невідомі - пропускаємо
        if birth is None and death is None:
            return results
        
        if birth is not None and death is not None:
            # T1: Смерть раніше народження
            if death < birth:
                results.append(ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    code="T1_DEATH_BEFORE_BIRTH",
                    message=f"Дата смерті ({death_year}) раніше народження ({birth_year})"
                ))
            
            # Z3: Занадто старий
            age = death - birth
            if age > self.MAX_HUMAN_AGE:
                results.append(ValidationResult(
                    valid=True,
                    level=ValidationLevel.WARNING,
                    code="Z3_UNREALISTIC_AGE",
                    message=f"Вік {age} років перевищує реалістичний максимум ({self.MAX_HUMAN_AGE})"
                ))
        
        # Z3: Безсмертний горець
        if birth is not None and death is None:
            age = self.CURRENT_YEAR - birth
            if age > self.MAX_HUMAN_AGE:
                results.append(ValidationResult(
                    valid=True,
                    level=ValidationLevel.WARNING,
                    code="Z3_IMMORTAL",
                    message=f"Особа народжена {birth_year} ({age} років тому) і досі жива?"
                ))
        
        return results
    
    def validate_parent_child_dates(
        self,
        parent_birth: Union[str, int, None],
        parent_death: Union[str, int, None],
        child_birth: Union[str, int, None],
        parent_gender: Optional[str] = None
    ) -> List[ValidationResult]:
        """T2-T4: Перевірка дат батько-дитина (з підтримкою гнучких дат)"""
        results = []
        
        # Розпарсити дати
        p_birth = self._resolve(parent_birth)
        p_death = self._resolve(parent_death)
        c_birth = self._resolve(child_birth)
        
        # Якщо основні дати невідомі - пропускаємо
        if p_birth is None or c_birth is None:
            results.append(ValidationResult(
                valid=True,
                level=ValidationLevel.SKIPPED,
                code="T_SKIPPED",
                message="Дати невідомі - валідація пропущена"
            ))
            return results
        
        parent_age_at_birth = c_birth - p_birth
        
        # T2: Батько з майбутнього
        if parent_age_at_birth <= 0:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="T2_PARENT_YOUNGER",
                message=f"Батько/мати народився пізніше за дитину"
            ))
            return results
        
        # B1: Занадто молодий батько
        if parent_age_at_birth < self.MIN_PARENT_AGE:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="B1_PARENT_TOO_YOUNG",
                message=f"Батько/мати мав(ла) {parent_age_at_birth} років при народженні дитини"
            ))
        
        # B2: Занадто стара мати
        if parent_gender == "F" and parent_age_at_birth > self.MAX_MOTHER_AGE:
            results.append(ValidationResult(
                valid=True,
                level=ValidationLevel.WARNING,
                code="B2_MOTHER_TOO_OLD",
                message=f"Матері було {parent_age_at_birth} років при народженні"
            ))
        
        # T3/T4: Дитина після смерті батька
        if p_death is not None:
            years_after_death = c_birth - p_death
            
            if parent_gender == "F" and years_after_death > 0:
                # T3: Мати-привид
                results.append(ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    code="T3_MOTHER_GHOST",
                    message=f"Дитина народилася через {years_after_death} років після смерті матері"
                ))
            elif parent_gender == "M" and years_after_death > self.MAX_FATHER_POSTHUMOUS:
                # T4: Батько-привид
                results.append(ValidationResult(
                    valid=True,
                    level=ValidationLevel.WARNING,
                    code="T4_FATHER_GHOST",
                    message=f"Дитина народилася через {years_after_death} років після смерті батька"
                ))
        
        return results
    
    def validate_marriage_dates(
        self,
        person_birth: Union[str, int, None],
        person_death: Union[str, int, None],
        marriage_year: Union[str, int, None],
        divorce_year: Union[str, int, None] = None
    ) -> List[ValidationResult]:
        """T5-T6, Z1: Перевірка дат шлюбу (з підтримкою гнучких дат)"""
        results = []
        
        # Розпарсити дати
        birth = self._resolve(person_birth)
        death = self._resolve(person_death)
        marriage = self._resolve(marriage_year)
        divorce = self._resolve(divorce_year)
        
        if marriage is None:
            return results
        
        # T5: Шлюб у дитсадку
        if birth is not None:
            age_at_marriage = marriage - birth
            if age_at_marriage < self.MIN_MARRIAGE_AGE:
                level = ValidationLevel.ERROR if age_at_marriage < 10 else ValidationLevel.WARNING
                results.append(ValidationResult(
                    valid=level == ValidationLevel.WARNING,
                    level=level,
                    code="T5_CHILD_MARRIAGE",
                    message=f"Шлюб у віці {age_at_marriage} років"
                ))
        
        # T6: Розлучення до весілля
        if divorce is not None and divorce < marriage:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="T6_DIVORCE_BEFORE_MARRIAGE",
                message=f"Розлучення ({divorce_year}) раніше шлюбу ({marriage_year})"
            ))
        
        # Z1: Весілля з того світу
        if death is not None and marriage > death:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="Z1_MARRIAGE_AFTER_DEATH",
                message=f"Шлюб ({marriage_year}) після смерті ({person_death})"
            ))
        
        return results
    
    # ==================== C: Топологічні парадокси ====================
    
    def validate_self_reference(
        self,
        person1_id: str,
        person2_id: str,
        relation_type: str
    ) -> List[ValidationResult]:
        """C1, C2, C4: Перевірка самопосилань"""
        results = []
        
        if person1_id == person2_id:
            code_map = {
                "SPOUSE": ("C1_SELF_MARRIAGE", "Неможливо одружитися на собі"),
                "PARENT_OF": ("C2_SELF_PARENT", "Неможливо бути своїм батьком"),
                "CHILD_OF": ("C2_SELF_CHILD", "Неможливо бути своєю дитиною"),
                "SIBLING": ("C4_SELF_SIBLING", "Неможливо бути своїм братом/сестрою"),
            }
            code, msg = code_map.get(relation_type, ("C0_SELF_REF", "Самопосилання заборонені"))
            
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code=code,
                message=msg
            ))
        
        return results
    
    def validate_no_cycle(
        self,
        person_id: str,
        potential_parent_id: str,
        get_ancestors_func
    ) -> List[ValidationResult]:
        """C3: Перевірка циклів у графі"""
        results = []
        
        ancestors = get_ancestors_func(person_id)
        
        if potential_parent_id in ancestors:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="C3_CYCLE_DETECTED",
                message="Виявлено цикл: ця особа є нащадком того, кого ви хочете зробити батьком"
            ))
        
        return results
    
    # ==================== B: Біологічні обмеження ====================
    
    def validate_biological_parents_count(
        self,
        current_parents: List[Dict],
        new_parent_type: str = "biological"
    ) -> List[ValidationResult]:
        """B4: Перевірка кількості біологічних батьків"""
        results = []
        
        if new_parent_type != "biological":
            return results
        
        bio_parents = [p for p in current_parents if p.get("is_biological", True)]
        
        if len(bio_parents) >= 2:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="B4_THREE_PARENTS",
                message="У людини може бути лише 2 біологічних батьків. Використовуйте 'усиновлення' для третього."
            ))
        
        return results
    
    def validate_incest(
        self,
        person1_id: str,
        person2_id: str,
        get_siblings_func
    ) -> List[ValidationResult]:
        """B3: Перевірка інцесту"""
        results = []
        
        siblings = get_siblings_func(person1_id)
        sibling_ids = [s["id"] for s in siblings]
        
        if person2_id in sibling_ids:
            results.append(ValidationResult(
                valid=True,
                level=ValidationLevel.WARNING,
                code="B3_INCEST",
                message="⚠️ Шлюб між братом і сестрою. Ви впевнені?"
            ))
        
        return results
    
    # ==================== M: Багатоженство ====================
    
    def validate_active_marriages(
        self,
        current_spouses: List[Dict],
        allow_polygamy: bool = False
    ) -> List[ValidationResult]:
        """M1: Перевірка активних шлюбів"""
        results = []
        
        active_marriages = [
            s for s in current_spouses 
            if s.get("marriage_status") == "married"
        ]
        
        if active_marriages and not allow_polygamy:
            results.append(ValidationResult(
                valid=False,
                level=ValidationLevel.ERROR,
                code="M1_POLYGAMY",
                message=f"Особа вже має активний шлюб. Спочатку оформіть розлучення або вкажіть смерть партнера."
            ))
        
        return results
    
    def validate_duplicate(
        self,
        name: str,
        birth_year: Union[str, int, None],
        existing_persons: List[Dict]
    ) -> List[ValidationResult]:
        """M2: Перевірка дублікатів"""
        results = []
        
        birth = self._resolve(birth_year)
        
        for person in existing_persons:
            existing_birth = self._resolve(person.get("birth_year"))
            if (person.get("name", "").lower() == name.lower() and 
                existing_birth == birth):
                results.append(ValidationResult(
                    valid=True,
                    level=ValidationLevel.WARNING,
                    code="M2_DUPLICATE",
                    message=f"Можливий дублікат: '{name}' ({birth_year}) вже існує в дереві"
                ))
                break
        
        return results
    
    # ==================== Комплексна валідація ====================
    
    def validate_person(
        self,
        name: str,
        birth_year: Union[str, int, None] = None,
        death_year: Union[str, int, None] = None,
        gender: Optional[str] = None,
        existing_persons: List[Dict] = None
    ) -> Tuple[bool, List[ValidationResult]]:
        """Повна валідація особи"""
        results = []
        
        results.extend(self.validate_birth_death(birth_year, death_year))
        
        if existing_persons:
            results.extend(self.validate_duplicate(name, birth_year, existing_persons))
        
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        is_valid = len(errors) == 0
        
        return is_valid, results
    
    def validate_parent_relationship(
        self,
        parent: Dict,
        child: Dict,
        existing_parents: List[Dict] = None,
        is_biological: bool = True
    ) -> Tuple[bool, List[ValidationResult]]:
        """Повна валідація батьківського зв'язку"""
        results = []
        
        results.extend(self.validate_self_reference(
            parent.get("id", ""), child.get("id", ""), "PARENT_OF"
        ))
        
        results.extend(self.validate_parent_child_dates(
            parent.get("birth_year"),
            parent.get("death_year"),
            child.get("birth_year"),
            parent.get("gender")
        ))
        
        if existing_parents and is_biological:
            results.extend(self.validate_biological_parents_count(
                existing_parents, "biological" if is_biological else "adopted"
            ))
        
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        return len(errors) == 0, results
    
    def validate_spouse_relationship(
        self,
        person1: Dict,
        person2: Dict,
        marriage_year: Union[str, int, None] = None,
        divorce_year: Union[str, int, None] = None,
        current_spouses: List[Dict] = None,
        get_siblings_func = None
    ) -> Tuple[bool, List[ValidationResult]]:
        """Повна валідація шлюбу"""
        results = []
        
        results.extend(self.validate_self_reference(
            person1.get("id", ""), person2.get("id", ""), "SPOUSE"
        ))
        
        results.extend(self.validate_marriage_dates(
            person1.get("birth_year"),
            person1.get("death_year"),
            marriage_year,
            divorce_year
        ))
        
        results.extend(self.validate_marriage_dates(
            person2.get("birth_year"),
            person2.get("death_year"),
            marriage_year,
            divorce_year
        ))
        
        if current_spouses:
            results.extend(self.validate_active_marriages(current_spouses))
        
        if get_siblings_func:
            results.extend(self.validate_incest(
                person1.get("id", ""), person2.get("id", ""), get_siblings_func
            ))
        
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        return len(errors) == 0, results


# ==================== Утиліти ====================

def format_validation_results(results: List[ValidationResult]) -> str:
    """Форматувати результати для виводу"""
    if not results:
        return "✅ Валідація пройшла успішно"
    
    lines = []
    errors = [r for r in results if r.level == ValidationLevel.ERROR]
    warnings = [r for r in results if r.level == ValidationLevel.WARNING]
    skipped = [r for r in results if r.level == ValidationLevel.SKIPPED]
    
    if errors:
        lines.append("❌ ПОМИЛКИ:")
        for r in errors:
            lines.append(f"   {r}")
    
    if warnings:
        lines.append("⚠️ ПОПЕРЕДЖЕННЯ:")
        for r in warnings:
            lines.append(f"   {r}")
    
    if skipped:
        lines.append("⏭️ ПРОПУЩЕНО:")
        for r in skipped:
            lines.append(f"   {r}")
    
    return "\n".join(lines)
