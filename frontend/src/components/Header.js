import React from 'react';
import './Header.css';

function Header({ onAddClick, isEncrypted, onToggleEncryption }) {
  return (
    <header className="diia-header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="header-title">
            <span className="header-icon">🌳</span>
            Родовід
          </h1>
          <p className="header-subtitle">Мій Рід</p>
        </div>
        
        <div className="header-actions">
          <button 
            className="diia-btn btn-secondary"
            onClick={onToggleEncryption}
            title={isEncrypted ? "Розшифрувати" : "Зашифрувати"}
          >
            <span>{isEncrypted ? '🔒' : '🔓'}</span>
            <span>{isEncrypted ? 'Зашифровано' : 'Розшифровано'}</span>
          </button>
          
          <button 
            className="diia-btn btn-primary"
            onClick={onAddClick}
          >
            <span>➕</span>
            <span>Додати родича</span>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;

