# Frontend - React + D3.js

React застосунок для візуалізації родинного дерева.

## 🚀 Запуск

```bash
# Встановіть залежності (перший раз)
npm install

# Запустіть dev сервер
npm start
```

Відкрийте http://localhost:3000

## 📁 Структура

```
frontend/
├── public/
│   └── index.html           # HTML template
├── src/
│   ├── components/
│   │   ├── TreeView.js      # D3 візуалізація дерева
│   │   ├── TreeView.css
│   │   ├── PersonModal.js   # Модалка з деталями персони
│   │   ├── PersonModal.css
│   │   ├── SearchPanel.js   # Пошук в архівах
│   │   ├── SearchPanel.css
│   │   ├── Header.js        # Верхня панель
│   │   └── Header.css
│   ├── utils/
│   │   ├── crypto.js        # AES-256-GCM шифрування
│   │   ├── api.js           # Backend API клієнт
│   │   └── adapter.js       # Адаптери даних
│   ├── App.js               # Головний компонент
│   ├── App.css
│   └── index.js             # React entry point
└── package.json
```

## 🎨 Компоненти

### TreeView
Візуалізація родинного дерева з D3.js

**Props:**
- `data` - Дані дерева `{nodes, links}`
- `isEncrypted` - Чи показувати зашифровані дані
- `onNodeClick` - Callback при кліку на персону
- `selectedNode` - Вибрана персона

**Features:**
- Zoom/Pan навігація
- Автоматична побудова сімейних груп (батько + мати + діти)
- Знаходження кореневого предка
- Highlight вибраної персони

### PersonModal
Модальне вікно з деталями персони

**Props:**
- `isOpen` - Чи відкрита модалка
- `person` - Дані персони
- `onClose` - Callback закриття
- `onSave` - Callback збереження
- `onDelete` - Callback видалення
- `mode` - `'add'` або `'edit'`

### SearchPanel
Панель пошуку в архівах

**Props:**
- `userId` - ID користувача
- `onResultSelect` - Callback вибору результату

## 🔐 Шифрування

### CryptoModule (`utils/crypto.js`)

```javascript
import { CryptoModule } from './utils/crypto';

// Ініціалізація (автоматично при завантаженні)
await CryptoModule.init();

// Шифрування
const encrypted = await CryptoModule.encrypt('Іван Петренко');
// Повертає: "ENC_Uj3k8xL9..."

// Розшифровка
const decrypted = await CryptoModule.decrypt(encrypted);
// Повертає: "Іван Петренко"

// Тестові дані (без реального шифрування)
const testEncrypted = "ENC_fake_Тестове Ім'я";
// Розшифровується як: "Тестове Ім'я"
```

Ключі зберігаються в IndexedDB браузера.

## 📡 API (`utils/api.js`)

```javascript
import { API } from './utils/api';

// Отримати дерево
const tree = await API.getTree('user_1');

// Додати персону
await API.addPerson({
  user_id: 'user_1',
  name_blob: 'ENC_...',
  birth_date_blob: 'ENC_...',
  relation: 'CHILD',
  link_to_person_id: 'person_xyz'
});

// Видалити персону
await API.deletePerson('person_xyz');

// Пошук в архівах
const results = await API.searchArchives('Іван Коваленко', 5);
```

## 🎨 Стилі

### CSS змінні

```css
:root {
  --primary-color: #4CAF50;
  --danger-color: #f44336;
  --warning-color: #ff9800;
  --text-primary: #333;
  --text-secondary: #666;
  --border-color: #ddd;
}
```

### Адаптивність
- Desktop: ≥768px
- Mobile: <768px

## 🧪 Тестування

```bash
# Запустити тести
npm test

# Watch mode
npm test -- --watch

# Покриття
npm test -- --coverage
```

## 📦 Build

```bash
# Production build
npm run build

# Результат в папці build/
```

## 🔨 Розробка

### Додати новий компонент

```jsx
// components/NewComponent.js
import React from 'react';
import './NewComponent.css';

function NewComponent({ prop1, prop2 }) {
  return (
    <div className="new-component">
      {/* JSX */}
    </div>
  );
}

export default NewComponent;
```

### Використати в App.js

```jsx
import NewComponent from './components/NewComponent';

function App() {
  return (
    <div className="app">
      <NewComponent prop1="value" />
    </div>
  );
}
```

### Hot Module Replacement
Dev сервер автоматично перезавантажує при змінах.

## 🐛 Debugging

### React DevTools
1. Встановіть [React DevTools](https://react.dev/learn/react-developer-tools)
2. Відкрийте в Chrome/Firefox
3. Переглядайте component tree та state

### Console logs
```javascript
console.log('[Component]', variable);
```

### Breakpoints
1. Відкрийте DevTools (F12)
2. Sources → файл
3. Клік на номер рядка

## ⚠️ Типові проблеми

**"Module not found"**
```bash
npm install
```

**"Port 3000 already in use"**
```bash
# Змініть порт в package.json
"start": "PORT=3001 react-scripts start"
```

**Дерево не відображається**
1. Перевірте console (F12) на помилки
2. Перевірте чи backend працює: http://localhost:8000
3. Перевірте CORS налаштування backend
4. Hard refresh: Ctrl+Shift+R

**Шифрування не працює**
1. Перевірте IndexedDB в DevTools → Application
2. Очистіть IndexedDB та перезавантажте
3. Перевірте чи браузер підтримує Web Crypto API

## 📚 Документація

- [React Docs](https://react.dev/)
- [D3.js Docs](https://d3js.org/)
- [Web Crypto API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)

