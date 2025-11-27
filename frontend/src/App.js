import React, { useState, useEffect } from 'react';
import './App.css';
import Header from './components/Header';
import TreeView from './components/TreeView';
import SearchPanel from './components/SearchPanel';
import PersonModal from './components/PersonModal';
import BackendStatus from './components/BackendStatus';
import { CryptoModule } from './utils/crypto';
import { API } from './utils/api';
import { adaptPersonDataForBackend, extractYearFromDate } from './utils/adapter';

function App() {
  const [treeData, setTreeData] = useState({ nodes: [], links: [] });
  const [decryptedTreeData, setDecryptedTreeData] = useState({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [decryptedSelectedNode, setDecryptedSelectedNode] = useState(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isEncrypted, setIsEncrypted] = useState(true);
  const [loading, setLoading] = useState(true);
  const [userId] = useState('user_1'); // TODO: отримувати з Дія.Підпис
  const [searchPersonData, setSearchPersonData] = useState(null);
  const decryptCacheRef = React.useRef(new Map()); // Кеш для розшифровки

  // Завантаження дерева при старті
  useEffect(() => {
    loadTree();
  }, []);

  const loadTree = async () => {
    try {
      setLoading(true);
      const data = await API.getTree(userId);
      console.log('Tree data loaded:', data);
      
      // Перевіряємо структуру даних
      if (data && (data.nodes || data.links || data.relationships)) {
        // Адаптуємо relationships -> links (якщо потрібно)
        const links = data.links || (data.relationships || []).map(rel => ({
          source: rel.source_id,
          target: rel.target_id,
          type: rel.type
        }));
        
        const rawData = {
          nodes: data.nodes || [],
          links: links
        };
        setTreeData(rawData);
        
        // Розшифровуємо для модалки
        const decrypted = await decryptTreeForModal(rawData);
        setDecryptedTreeData(decrypted);
      } else {
        console.warn('Unexpected data format:', data);
        setTreeData({ nodes: [], links: [] });
        setDecryptedTreeData({ nodes: [], links: [] });
      }
    } catch (error) {
      console.error('Помилка завантаження дерева:', error);
      // Fallback - порожнє дерево
      setTreeData({ nodes: [], links: [] });
      setDecryptedTreeData({ nodes: [], links: [] });
    } finally {
      setLoading(false);
    }
  };

  const decryptTreeForModal = async (data) => {
    // Розшифровуємо імена для відображення в селекті
    const decryptedNodes = await Promise.all(
      data.nodes.map(async (node) => {
        const decryptedNode = { ...node };
        
        // Root користувач - спеціальна обробка
        if (node.is_root) {
          decryptedNode.name = 'Root User (Ви)';
          return decryptedNode;
        }
        
        // Ghost node - використовуємо ghost_name
        if (node.is_deleted) {
          decryptedNode.name = node.ghost_name || '[Видалено]';
          return decryptedNode;
        }
        
        // Розшифровка ІМЕНІ з кешуванням
        if (node.name_blob && node.name_blob.startsWith('ENC_')) {
          // Перевірка на тестові дані (ENC_fake_)
          if (node.name_blob.startsWith('ENC_fake_')) {
            decryptedNode.name = node.name_blob.replace('ENC_fake_', '');
          } else {
            // Реальні зашифровані дані
            const cacheKey = `modal_name_${node.name_blob}`;
            if (decryptCacheRef.current.has(cacheKey)) {
              decryptedNode.name = decryptCacheRef.current.get(cacheKey);
            } else {
              try {
                const name = await CryptoModule.decrypt(node.name_blob);
                decryptCacheRef.current.set(cacheKey, name);
                decryptedNode.name = name;
              } catch (e) {
                console.warn(`⚠️ Failed to decrypt name for node ${node.id}:`, e.message);
                const fallbackName = `[Помилка даних: ${node.id.substring(0, 8)}...]`;
                decryptCacheRef.current.set(cacheKey, fallbackName);
                decryptedNode.name = fallbackName;
              }
            }
          }
        } else {
          // Fallback для порожніх або битих блобів
          decryptedNode.name = node.name || node.name_blob || `[ID: ${node.id.substring(0, 8)}...]`;
        }
        
        // Розшифровка NOTES з кешуванням
        if (node.private_notes_blob && node.private_notes_blob.startsWith('ENC_')) {
          // Перевірка на тестові дані (ENC_fake_)
          if (node.private_notes_blob.startsWith('ENC_fake_')) {
            decryptedNode.notes = node.private_notes_blob.replace('ENC_fake_', '');
          } else {
            // Реальні зашифровані дані
            const cacheKey = `modal_notes_${node.private_notes_blob}`;
            if (decryptCacheRef.current.has(cacheKey)) {
              decryptedNode.notes = decryptCacheRef.current.get(cacheKey);
            } else {
              try {
                const notes = await CryptoModule.decrypt(node.private_notes_blob);
                decryptCacheRef.current.set(cacheKey, notes);
                decryptedNode.notes = notes;
              } catch (e) {
                console.warn(`⚠️ Failed to decrypt notes for node ${node.id}:`, e.message);
                decryptedNode.notes = '';
              }
            }
          }
        } else {
          decryptedNode.notes = node.notes || '';
        }
        
        return decryptedNode;
      })
    );
    
    return { nodes: decryptedNodes, links: data.links };
  };

  const handleAddPerson = async (personData) => {
    try {
      console.log('[App] Додавання особи:', personData);
      
      // ✅ STEP 1: Extract birth_year_approx BEFORE encryption (needed for validation)
      const birthYearApprox = extractYearFromDate(personData.birthDate);
      if (!birthYearApprox) {
        alert('⚠️ Не вдалося визначити рік народження. Перевірте формат дати.');
        return false;
      }
      
      // ✅ STEP 2: Encrypt personal data (name, birthDate, notes)
      const nameBlob = await CryptoModule.encrypt(personData.name);
      const birthBlob = await CryptoModule.encrypt(personData.birthDate);
      const notesBlob = personData.notes && personData.notes.trim() 
        ? await CryptoModule.encrypt(personData.notes) 
        : null;

      // ✅ STEP 3: Create intermediate object with encrypted blobs AND plaintext data
      // (Adapter needs plaintext dates to extract years and encrypt death_date)
      const encryptedData = {
        // Encrypted blobs (already encrypted)
        name_blob: nameBlob,
        birth_date_blob: birthBlob,
        private_notes_blob: notesBlob || null,
        
        // Plaintext data (needed by adapter for extraction/encryption)
        birthDate: personData.birthDate, // Plaintext - adapter will extract year
        deathDate: personData.deathDate || null, // Plaintext - adapter will encrypt
        gender: personData.gender || null, // Plaintext - adapter will pass through
        
        // Extracted validation data
        birthYearApprox: birthYearApprox, // Already extracted
        
        // Relationship data
        relation: personData.relation,
        linkToPersonId: personData.linkToPersonId, // Adapter will rename to link_to_id
        
        // Source data (adapter will convert to source_ids)
        source: personData.source || null
      };

      console.log('[App] Проміжні дані (перед адаптацією):', {
        name_blob: nameBlob.substring(0, 30) + '...',
        birth_date_blob: birthBlob.substring(0, 30) + '...',
        birthYearApprox: birthYearApprox,
        relation: encryptedData.relation,
        linkToPersonId: encryptedData.linkToPersonId
      });

      // ✅ STEP 4: Transform using adapter (encrypts death_date, extracts years, fixes field names)
      const finalPayload = await adaptPersonDataForBackend(encryptedData);
      
      console.log('[App] Фінальний payload (після адаптації):', {
        ...finalPayload,
        name_blob: finalPayload.name_blob?.substring(0, 30) + '...',
        birth_date_blob: finalPayload.birth_date_blob?.substring(0, 30) + '...',
        death_date_blob: finalPayload.death_date_blob?.substring(0, 30) + '...',
        birth_year_approx: finalPayload.birth_year_approx,
        link_to_id: finalPayload.link_to_id
      });

      // ✅ STEP 5: Send adapted payload to backend
      const response = await API.addPerson(finalPayload, userId);
      
      console.log('[App] Відповідь сервера:', response);
      
      if (response.success) {
        await loadTree(); // Перезавантажуємо дерево
        setIsAddModalOpen(false);
        alert('✅ Особу успішно додано!');
        return true;
      } else {
        alert(`❌ Помилка: ${response.message || 'Невідома помилка'}`);
        return false;
      }
    } catch (error) {
      console.error('[App] Помилка додавання особи:', error);
      console.error('[App] Stack trace:', error.stack);
      
      // Enhanced error handling
      let errorMessage = 'Невідома помилка';
      if (error.message) {
        errorMessage = error.message;
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      alert(`❌ Помилка додавання особи: ${errorMessage}`);
      return false;
    }
  };

  const handleToggleEncryption = () => {
    setIsEncrypted(!isEncrypted);
  };

  const handleDeletePerson = async (personId) => {
    if (!personId) {
      alert('Виберіть особу для видалення');
      return;
    }

    if (!window.confirm(`Ви впевнені що хочете видалити цю особу? Ця дія незворотня!`)) {
      return;
    }

    try {
      console.log('[App] Видалення особи:', personId);
      await API.deletePerson(personId);
      alert('✅ Особу видалено');
      // Оновлюємо дерево
      await loadTree();
      setSelectedNode(null);
      setDecryptedSelectedNode(null);
    } catch (error) {
      console.error('[App] Помилка видалення:', error);
      alert(`❌ Помилка: ${error.message}`);
    }
  };

  return (
    <div className="App">
      <Header 
        onAddClick={() => setIsAddModalOpen(true)}
        isEncrypted={isEncrypted}
        onToggleEncryption={handleToggleEncryption}
      />
      
      <BackendStatus />
      
      <div className="app-content">
        <div className="sidebar">
          <SearchPanel onAddPerson={(personData) => {
            // Відкриваємо модальне вікно з заповненими даними
            setSelectedNode(null);
            setDecryptedSelectedNode(null);
            setSearchPersonData(personData);
            setIsAddModalOpen(true);
          }} />
        </div>
        
        <div className="main-content">
          {loading ? (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Завантаження дерева...</p>
            </div>
          ) : (
            <>
              <TreeView
                data={treeData}
                isEncrypted={isEncrypted}
                onNodeClick={(node) => {
                  setSelectedNode(node);
                  // Знаходимо розшифровану версію для модалки
                  if (node && decryptedTreeData.nodes) {
                    const decrypted = decryptedTreeData.nodes.find(n => n.id === node.id);
                    setDecryptedSelectedNode(decrypted || node);
                  } else {
                    setDecryptedSelectedNode(null);
                  }
                }}
                selectedNode={selectedNode}
              />
              {treeData.nodes.length === 0 && !loading && (
                <div className="empty-state card">
                  <h3>Дерево порожнє</h3>
                  <p>Додайте першого родича, натиснувши кнопку "Додати родича"</p>
                  <button 
                    className="btn btn-primary" 
                    onClick={() => setIsAddModalOpen(true)}
                    style={{ marginTop: '16px' }}
                  >
                    ➕ Додати першого родича
                  </button>
                </div>
              )}
              {selectedNode && (
                <div className="selected-node-info card" style={{ marginTop: '16px', padding: '16px' }}>
                  <h3>Вибрана особа</h3>
                  <p><strong>ПІБ:</strong> {selectedNode.name || '[Зашифровано]'}</p>
                  <p><strong>Рік народження:</strong> {selectedNode.birth || '[Зашифровано]'}</p>
                  {selectedNode.is_root && <p><em>🏠 Root користувач</em></p>}
                  <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
                    <button 
                      className="btn btn-danger" 
                      onClick={() => handleDeletePerson(selectedNode.id)}
                      disabled={selectedNode.is_root}
                      title={selectedNode.is_root ? 'Неможливо видалити root користувача' : 'Видалити цю особу'}
                    >
                      🗑️ Видалити
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {isAddModalOpen && (
        <PersonModal
          isOpen={isAddModalOpen}
          onClose={() => {
            setIsAddModalOpen(false);
            setSearchPersonData(null);
          }}
          onSubmit={handleAddPerson}
          treeData={decryptedTreeData}
          mode="add"
          initialData={searchPersonData}
        />
      )}

      {isEditModalOpen && decryptedSelectedNode && (
        <PersonModal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSubmit={handleAddPerson}
          treeData={decryptedTreeData}
          mode="edit"
          person={decryptedSelectedNode}
        />
      )}
    </div>
  );
}

export default App;

