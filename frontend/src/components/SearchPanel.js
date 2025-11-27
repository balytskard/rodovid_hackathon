import React, { useState } from 'react';
import './SearchPanel.css';
import { API } from '../utils/api';

function SearchPanel({ onAddPerson }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      const data = await API.searchArchives(query, 5);
      setResults(data.results || []);
    } catch (error) {
      console.error('Помилка пошуку:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAddFromSearch = (result) => {
    // Формуємо дані для додавання
    const personData = {
      name: result.title || '',
      birthDate: result.year || '',
      deathDate: '',
      notes: `Знайдено в архіві:\n${result.explanation}\nМісце: ${result.location}`,
      source: 'Архівний пошук'
    };
    
    if (onAddPerson) {
      onAddPerson(personData);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="search-panel card">
      <h2 className="panel-title">Пошук в архівах</h2>
      
      <div className="search-box">
        <input
          type="text"
          className="input"
          placeholder="Наприклад: Коваленко лікар Київ 1920"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button 
          className="btn btn-primary search-btn"
          onClick={handleSearch}
          disabled={loading}
        >
          {loading ? '⏳' : '🔍'}
        </button>
      </div>

      {results.length > 0 && (
        <div className="search-results">
          {results.map((result, idx) => (
            <div key={idx} className="result-card">
              <div className="result-header">
                <h3 className="result-title">{result.title}</h3>
                <span className="confidence-badge">
                  {Math.round(result.confidence_score * 100)}%
                </span>
              </div>
              <div className="result-meta">
                📅 {result.year} | 📍 {result.location}
              </div>
              <div className="result-explanation">
                💡 {result.explanation}
              </div>
              <button 
                className="btn btn-secondary btn-sm"
                onClick={() => handleAddFromSearch(result)}
                title="Додати до дерева"
              >
                ➕ Додати до дерева
              </button>
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && !loading && query && (
        <div className="empty-state">
          <p>Нічого не знайдено</p>
        </div>
      )}
    </div>
  );
}

export default SearchPanel;

