import React, { useState, useEffect } from 'react';
import { Folder, FileVideo, ChevronRight, CornerLeftUp } from 'lucide-react';

export function FolderBrowser({ onSelect, selectedPath }) {
  const [currentPath, setCurrentPath] = useState('');
  const [items, setItems] = useState([]);
  const [networkShares, setNetworkShares] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadDirectory = async (path) => {
    setLoading(true);
    setError(null);
    try {
      const url = path ? `/api/browser?path=${encodeURIComponent(path)}` : '/api/browser';
      const res = await fetch(url);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to load directory');
      }
      const data = await res.json();
      setItems(data);
      setCurrentPath(path || '');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch active network shares from the backend
    const fetchShares = async () => {
      try {
        const res = await fetch('/api/settings/network-mount');
        if (res.ok) {
          const data = await res.json();
          // The backend returns an object indexed by share path
          setNetworkShares(Object.keys(data || {}));
        }
      } catch (err) {
        console.error("Failed to sync network shares in browser:", err);
      }
    };
    
    fetchShares();
    loadDirectory('');
  }, []);

  useEffect(() => {
    onSelect(currentPath);
  }, [currentPath, onSelect]);

  const handleUp = () => {
    if (!currentPath) return;
    
    const isUNC = currentPath.startsWith('\\\\') || currentPath.startsWith('//');
    const parts = currentPath.replace(/\\/g, '/').split('/').filter(Boolean);
    
    if (parts.length <= 1) {
      loadDirectory('');
      return;
    }
    
    parts.pop();
    let parentPath = parts.join('\\');
    
    if (isUNC) {
      parentPath = '\\\\' + parentPath;
    } else if (parts.length === 1 && parentPath.endsWith(':')) {
      parentPath += '\\';
    }
    
    loadDirectory(parentPath);
  };

  return (
    <div className="glass-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h3>Select Folder or Video</h3>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', background: 'var(--panel-bg)', padding: '0.5rem', borderRadius: '8px' }}>
        <button onClick={handleUp} disabled={!currentPath} style={{ padding: '0.4rem', background: 'rgba(255,255,255,0.1)' }}>
          <CornerLeftUp size={16} />
        </button>
        <div style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
          {currentPath || 'Local Drives'}
        </div>
      </div>

      {error && <div style={{ color: 'var(--danger)', marginBottom: '1rem' }}>{error}</div>}

      <div style={{ 
        maxHeight: '300px', 
        overflowY: 'auto', 
        border: '1px solid var(--panel-border)', 
        borderRadius: '8px',
        background: 'rgba(0,0,0,0.2)'
      }}>
        {loading ? (
          <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
        ) : items.length === 0 && (!currentPath && networkShares.length === 0) ? (
          <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>Empty directory</div>
        ) : (
          <>
            {!currentPath && networkShares.length > 0 && (
              <div style={{ padding: '0.5rem 1rem', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 'bold' }}>NETWORK LOCATIONS</div>
            )}
            {!currentPath && networkShares.map((share, idx) => (
              <div 
                key={`net-${idx}`}
                onClick={() => loadDirectory(share)}
                className="browser-item"
              >
                <Folder size={20} color="var(--success)" />
                <span style={{ flex: 1, fontFamily: 'monospace' }}>{share}</span>
                <ChevronRight size={16} color="var(--text-muted)" />
              </div>
            ))}
            {!currentPath && (
              <div style={{ padding: '0.5rem 1rem', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 'bold' }}>LOCAL DRIVES</div>
            )}
            {items.map((item, idx) => (
              <div 
                key={idx}
                onClick={() => {
                  if (item.is_dir) {
                    loadDirectory(item.path);
                  } else {
                    onSelect(item.path);
                  }
                }}
                className={`browser-item ${selectedPath === item.path ? 'browser-item-selected' : ''}`}
              >
                {item.is_dir ? <Folder size={20} color="var(--primary)" /> : <FileVideo size={20} color="var(--text-muted)" />}
                <span style={{ flex: 1 }}>{item.name}</span>
                {item.is_dir && <ChevronRight size={16} color="var(--text-muted)" />}
              </div>
            ))}
        </>
        )}
      </div>
    </div>
  );
}
