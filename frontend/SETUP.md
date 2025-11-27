# Встановлення React Frontend

## Швидкий старт

### 1. Встановити Node.js

Завантажте та встановіть Node.js 16+ з https://nodejs.org/

### 2. Встановити залежності

```bash
cd frontend-react
npm install
```

### 3. Запустити

```bash
npm start
```

Відкриється автоматично на http://localhost:3000

## Структура проєкту

```
frontend-react/
├── public/
│   └── index.html          # HTML шаблон
├── src/
│   ├── components/         # React компоненти
│   │   ├── Header.js       # Заголовок (Дія стиль)
│   │   ├── TreeView.js     # Візуалізація дерева
│   │   ├── SearchPanel.js  # Пошук в архівах
│   │   └── PersonModal.js  # Модальне вікно
│   ├── utils/
│   │   ├── crypto.js       # E2E шифрування
│   │   └── api.js          # API клієнт
│   ├── App.js              # Головний компонент
│   └── index.js            # Точка входу
└── package.json
```

## Дія UI Стиль

Всі компоненти використовують:
- **Кольори**: Синій (#0057FF), білі картки
- **Градієнти**: Світло-блакитний фон
- **Типографіка**: System fonts (San Francisco, Segoe UI)
- **Картки**: Закруглені кути (12-16px), тіні
- **Кнопки**: Закруглені, з hover ефектами

## Інтеграція з Backend

Backend має бути запущений на:
- URL: `http://localhost:8000`
- Endpoints: `/api/v1/tree`, `/api/v1/person`, `/api/v1/search/magic`

## Мобільна версія

Всі компоненти responsive:
- Breakpoint: 768px
- Адаптивна навігація
- Модальні вікна на весь екран

## Проблеми?

### Помилка "Module not found"
```bash
rm -rf node_modules package-lock.json
npm install
```

### Порт 3000 зайнятий
```bash
PORT=3001 npm start
```

### CORS помилки
Перевірте що backend налаштований для CORS (вже налаштовано в main.py)

