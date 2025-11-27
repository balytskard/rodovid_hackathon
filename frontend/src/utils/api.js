/**
 * API Module для взаємодії з backend
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';
const SERVER_URL = 'http://localhost:8000'; // Корінь сервера для healthCheck

/**
 * Generic request wrapper
 */
const request = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  let body = options.body;

  // 🛡️ ЗАХИСТ ВІД ПОДВІЙНОЇ СЕРІАЛІЗАЦІЇ (Fix for 422 error)
  // Якщо body це об'єкт - перетворюємо в рядок.
  // Якщо це вже рядок - залишаємо як є.
  if (body && typeof body !== 'string') {
    body = JSON.stringify(body);
  }

  console.log(`[API] ${options.method || 'GET'} ${url}`, body ? JSON.parse(body) : '');

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      body,
    });

    // Обробка помилок HTTP
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error(`[API Error] ${endpoint}:`, errorData);
      
      let errorMessage = `Error ${response.status}: ${response.statusText}`;
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else {
            errorMessage = errorData.detail;
        }
      } else if (errorData.message) {
        errorMessage = errorData.message;
      }
      
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log(`[API] Response from ${endpoint}:`, data);
    return data;
  } catch (error) {
    // Обробка мережевих помилок (коли сервер лежить)
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
        console.error(`[API] Network error - перевірте що backend запущений`);
        throw new Error('Backend недоступний. Перевірте що сервер запущений на http://localhost:8000');
    }
    console.error(`[API Failed] ${endpoint}:`, error);
    throw error;
  }
};

export const API = {
  // Отримати дерево
  getTree: (userId = 'user_1') => {
    return request(`/tree?user_id=${userId}`);
  },

  // Додати особу
  addPerson: (personData, userId = 'user_1') => {
    return request('/person', {
      method: 'POST',
      headers: {
        'X-User-ID': userId
      },
      body: personData
    });
  },

  // Видалити особу
  deletePerson: (personId, userId = 'user_1') => {
    return request(`/person/${personId}`, {
      method: 'DELETE',
      headers: {
        'X-User-ID': userId
      }
    });
  },

  // Пошук в архівах
  searchArchives: (query, topK = 5) => {
    return request('/search/magic', {
        method: 'POST',
        body: {
            query,
            top_k: topK
        }
    });
  },

  // ✅ HEALTH CHECK (Повернули на місце!)
  healthCheck: async () => {
    try {
        // Стукаємо на корінь сервера, а не в API
        const response = await fetch(`${SERVER_URL}/`);
        // Якщо сервер відповів хоч щось (200 OK), значить він живий
        if (response.ok) {
            return true;
        }
        return false;
    } catch (error) {
        return false;
    }
  }
};