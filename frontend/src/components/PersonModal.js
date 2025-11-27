import React, { useState, useEffect } from 'react';
import './PersonModal.css';

function PersonModal({ isOpen, onClose, onSubmit, treeData, mode = 'add', person = null, initialData = null }) {
  const [formData, setFormData] = useState({
    name: '',
    birthDate: '',
    deathDate: '',
    gender: '', // ✅ Added gender field
    relation: 'CHILD',
    linkToPersonId: '',
    notes: '',
    source: '' // Джерело/документ
  });

  useEffect(() => {
    if (mode === 'edit' && person) {
      setFormData({
        name: person.name || '',
        birthDate: person.birth || '',
        deathDate: person.death || '',
        relation: 'CHILD',
        linkToPersonId: '',
        notes: person.notes || ''
      });
    } else if (mode === 'add' && initialData) {
      // Заповнюємо дані з пошуку - конвертуємо все в рядки!
      setFormData({
        name: String(initialData.name || ''),
        birthDate: String(initialData.birthDate || ''),
        deathDate: String(initialData.deathDate || ''),
        gender: String(initialData.gender || ''), // ✅ Added gender
        relation: 'CHILD',
        linkToPersonId: '',
        notes: String(initialData.notes || ''),
        source: String(initialData.source || '')
      });
    }
  }, [mode, person, initialData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Конвертуємо всі поля в рядки для безпеки
    const cleanData = {
      name: String(formData.name || ''),
      birthDate: String(formData.birthDate || ''),
      deathDate: String(formData.deathDate || ''),
      gender: formData.gender || '', // ✅ Added gender
      relation: formData.relation,
      linkToPersonId: formData.linkToPersonId,
      notes: String(formData.notes || ''),
      source: String(formData.source || '')
    };
    
    if (!cleanData.name.trim()) {
      alert('Заповніть ПІБ');
      return;
    }

    if (!cleanData.birthDate.trim()) {
      alert('Заповніть рік народження');
      return;
    }

    if (mode === 'add') {
      if (!cleanData.linkToPersonId) {
        alert('Виберіть особу для зв\'язку');
        return;
      }
      
      // Якщо дерево порожнє і linkToPersonId не вибраний, використовуємо root
      if (!cleanData.linkToPersonId && treeData.nodes.length === 0) {
        cleanData.linkToPersonId = 'root_user_1';
      }
    }

    console.log('[PersonModal] Відправка даних:', cleanData);

    const success = await onSubmit(cleanData);
    if (success) {
      setFormData({
        name: '',
        birthDate: '',
        deathDate: '',
        gender: '', // ✅ Added gender reset
        relation: 'PARENT',
        linkToPersonId: '',
        notes: ''
      });
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{mode === 'add' ? 'Додати родича' : 'Редагувати'}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>ПІБ *</label>
            <input
              type="text"
              className="input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Іван Іванович Коваленко"
              required
            />
          </div>

          <div className="form-group">
            <label>Стать</label>
            <select
              className="input"
              value={formData.gender}
              onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
            >
              <option value="">Не вказано</option>
              <option value="M">Чоловік</option>
              <option value="F">Жінка</option>
            </select>
            <small style={{fontSize: '11px', color: '#666', marginTop: '4px', display: 'block'}}>
              Використовується для валідації родинних зв'язків
            </small>
          </div>

          <div className="form-group">
            <label>Рік народження *</label>
            <input
              type="text"
              className="input"
              value={formData.birthDate}
              onChange={(e) => setFormData({ ...formData, birthDate: e.target.value })}
              placeholder="1940"
              required
            />
          </div>

          <div className="form-group">
            <label>Рік смерті (опціонально)</label>
            <input
              type="text"
              className="input"
              value={formData.deathDate}
              onChange={(e) => setFormData({ ...formData, deathDate: e.target.value })}
              placeholder="2015"
            />
          </div>

          {mode === 'add' && (
            <>
              <div className="form-group">
                <label>Додати до</label>
                <select
                  className="input"
                  value={formData.linkToPersonId}
                  onChange={(e) => setFormData({ ...formData, linkToPersonId: e.target.value })}
                  required
                >
                  <option value="">Виберіть особу</option>
                  {treeData.nodes && treeData.nodes.length > 0 ? (
                    treeData.nodes.map(node => (
                      <option key={node.id} value={node.id}>
                        {node.name || node.name_blob || node.id}
                      </option>
                    ))
                  ) : (
                    <option value="root_user_1">Root User (створюється автоматично)</option>
                  )}
                </select>
              </div>

              <div className="form-group">
                <label>Зв'язок</label>
                <select
                  className="input"
                  value={formData.relation}
                  onChange={(e) => setFormData({ ...formData, relation: e.target.value })}
                >
                  <option value="CHILD">Дитина (я додаю дитину)</option>
                  <option value="PARENT">Батько/Мати (я додаю батька/матір)</option>
                  <option value="SPOUSE">Подружжя (чоловік/дружина)</option>
                  <option value="SIBLING">Брат/Сестра</option>
                </select>
                <small style={{fontSize: '11px', color: '#666', marginTop: '4px', display: 'block'}}>
                  {formData.relation === 'CHILD' && '→ Додається як дитина вибраної особи'}
                  {formData.relation === 'PARENT' && '→ Додається як батько/мати вибраної особи'}
                  {formData.relation === 'SPOUSE' && '→ Додається як подружжя вибраної особи'}
                  {formData.relation === 'SIBLING' && '→ Додається як брат/сестра вибраної особи'}
                </small>
              </div>
            </>
          )}

          <div className="form-group">
            <label>Приватні нотатки (зашифровано E2E)</label>
            <textarea
              className="input"
              rows="3"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Приватна інформація..."
            />
          </div>

          <div className="form-group">
            <label>Джерело/Документ</label>
            <input
              type="text"
              className="input"
              value={formData.source}
              onChange={(e) => setFormData({ ...formData, source: e.target.value })}
              placeholder="Наприклад: Метрична книга №123, Архівний запис..."
            />
            <small style={{fontSize: '11px', color: '#666', marginTop: '4px', display: 'block'}}>
              📄 Посилання на архівний документ або його опис
            </small>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Скасувати
            </button>
            <button type="submit" className="btn btn-primary">
              <span>🔒</span>
              {mode === 'add' ? 'Зберегти (E2E)' : 'Оновити'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default PersonModal;

