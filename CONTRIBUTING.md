# 🤝 Contributing to Rodovid

Дякуємо за інтерес до проекту! Ми раді вашому внеску.

## 📋 Як допомогти

### 🐛 Знайшли баг?
1. Перевірте чи вже є [Issue](https://github.com/your-org/rodovid/issues)
2. Якщо немає - створіть новий з:
   - Чіткою назвою та описом
   - Кроками для відтворення
   - Очікуваним та актуальним результатом
   - Версією Python/Node.js
   - Логами помилок

### 💡 Є ідея функції?
1. Створіть Issue з міткою `enhancement`
2. Опишіть:
   - Яку проблему вирішує
   - Як має працювати
   - Можливі альтернативи

### 🔧 Хочете написати код?

#### 1. Fork та Clone
```bash
# Fork на GitHub, потім:
git clone https://github.com/your-username/rodovid.git
cd rodovid
```

#### 2. Створіть гілку
```bash
git checkout -b feature/amazing-feature
# або
git checkout -b fix/critical-bug
```

#### 3. Встановіть залежності
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

#### 4. Зробіть зміни
- Дотримуйтесь стилю коду проекту
- Додайте коментарі до складної логіки
- Напишіть тести для нової функціональності

#### 5. Перевірте код

**Backend:**
```bash
# Тести
pytest tests/

# Linting
flake8 .
black . --check
mypy .
```

**Frontend:**
```bash
# Тести
npm test

# Linting
npm run lint

# Build
npm run build
```

#### 6. Commit
```bash
git add .
git commit -m "feat: Add amazing new feature"
```

Використовуйте [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - нова функція
- `fix:` - виправлення бага
- `docs:` - документація
- `style:` - форматування
- `refactor:` - рефакторинг
- `test:` - тести
- `chore:` - інше

#### 7. Push та Pull Request
```bash
git push origin feature/amazing-feature
```

Потім на GitHub:
1. Відкрийте Pull Request
2. Опишіть зміни
3. Прикріпіть screenshot (якщо UI)
4. Чекайте review

## 📝 Code Style

### Python
- PEP 8
- Black formatter
- Type hints де можливо
- Docstrings для функцій

```python
def process_data(input: str, max_length: int = 100) -> dict:
    """
    Process input data and return result.
    
    Args:
        input: The data to process
        max_length: Maximum allowed length
        
    Returns:
        Dictionary with processed data
        
    Raises:
        ValueError: If input is invalid
    """
    # Implementation
    pass
```

### JavaScript/React
- ESLint rules
- Prettier formatter
- JSDoc коментарі
- Functional components з hooks

```javascript
/**
 * TreeView component для візуалізації родинного дерева
 * 
 * @param {Object} props - Component props
 * @param {Object} props.data - Tree data {nodes, links}
 * @param {boolean} props.isEncrypted - Show encrypted data
 * @param {Function} props.onNodeClick - Node click handler
 * @returns {JSX.Element}
 */
function TreeView({ data, isEncrypted, onNodeClick }) {
  // Implementation
}
```

## 🧪 Тестування

### Backend тести
```bash
# Всі тести
pytest

# Конкретний модуль
pytest tests/test_validators.py

# З покриттям
pytest --cov=. --cov-report=html
```

### Frontend тести
```bash
# Unit тести
npm test

# E2E тести
npm run test:e2e

# Покриття
npm test -- --coverage
```

## 📚 Документація

При додаванні нової функції:
1. Оновіть README.md
2. Додайте JSDoc/Docstring
3. Оновіть docs/API.md (якщо API)
4. Додайте приклад використання

## ✅ Checklist перед Pull Request

- [ ] Код працює локально
- [ ] Всі тести проходять
- [ ] Додано нові тести (якщо потрібно)
- [ ] Документація оновлена
- [ ] Код відформатовано (Black/Prettier)
- [ ] Коміти зрозумілі та атомарні
- [ ] PR має чітку назву та опис

## 🚫 Що НЕ приймається

- Код без тестів (для нової функціональності)
- Незрозумілі коміти ("fix", "update", "wip")
- Порушення стилю коду
- Ламання існуючої функціональності
- Збільшення розміру bundle без причини

## 💬 Спілкування

- GitHub Issues - для багів та функцій
- GitHub Discussions - для обговорень
- Code Review коментарі - технічні питання

## 📄 Ліцензія

Відправляючи Pull Request, ви погоджуєтесь що ваш код буде під MIT License.

---

**Дякуємо за ваш внесок! 🎉**
