import React, { useState, useEffect } from 'react';
import { API } from '../utils/api';

function BackendStatus() {
  const [status, setStatus] = useState('checking');
  const [error, setError] = useState(null);

  useEffect(() => {
    checkBackend();
    const interval = setInterval(checkBackend, 10000); // Перевіряємо кожні 10 секунд
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      const isHealthy = await API.healthCheck();
      setStatus(isHealthy ? 'connected' : 'disconnected');
      setError(null);
    } catch (err) {
      setStatus('disconnected');
      setError(err.message);
    }
  };

  if (status === 'checking') {
    return (
      <div className="backend-status checking">
        <span>⏳ Перевірка підключення...</span>
      </div>
    );
  }

  if (status === 'disconnected') {
    return (
      <div className="backend-status error" style={{
        padding: '12px',
        background: '#FFEBEE',
        border: '1px solid #F44336',
        borderRadius: '8px',
        margin: '16px',
        color: '#C62828'
      }}>
        <strong>⚠️ Backend недоступний</strong>
        <p style={{ fontSize: '12px', marginTop: '4px' }}>
          Запустіть backend: <code>cd backend && python -m uvicorn main:app --reload --port 8000</code>
        </p>
        {error && <p style={{ fontSize: '12px', marginTop: '4px' }}>{error}</p>}
      </div>
    );
  }

  return (
    <div className="backend-status success" style={{
      padding: '8px 12px',
      background: '#E8F5E9',
      border: '1px solid #4CAF50',
      borderRadius: '8px',
      margin: '16px',
      color: '#2E7D32',
      fontSize: '12px'
    }}>
      ✅ Backend підключено
    </div>
  );
}

export default BackendStatus;

