import React, { useState, useEffect } from 'react';
import { Book, Plus, Trash2, Globe, ArrowRight } from 'lucide-react';

export function Glossary() {
  const [entries, setEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLang, setTargetLang] = useState('de');
  const [sourceTerm, setSourceTerm] = useState('');
  const [targetTerm, setTargetTerm] = useState('');
  const [status, setStatus] = useState('');

  const fetchGlossary = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/glossary/');
      if (res.ok) {
        const data = await res.json();
        setEntries(data || []);
      }
    } catch (err) {
      console.error('Failed to fetch glossary', err);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchGlossary();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!sourceTerm || !targetTerm) return;

    setStatus('Adding...');
    try {
      const res = await fetch('/api/glossary/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_lang: sourceLang,
          target_lang: targetLang,
          source_term: sourceTerm,
          target_term: targetTerm
        })
      });
      if (res.ok) {
        setSourceTerm('');
        setTargetTerm('');
        setStatus('Added successfully');
        fetchGlossary();
        setTimeout(() => setStatus(''), 3000);
      } else {
        setStatus('Error adding entry');
      }
    } catch (err) {
      setStatus('Error adding entry');
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`/api/glossary/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchGlossary();
      }
    } catch (err) {
      console.error('Failed to delete', err);
    }
  };

  return (
    <div className="settings-container animate-fade-in" style={{ paddingBottom: '2rem' }}>
      <div className="settings-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', width: '100%', maxWidth: '1000px', margin: '0 auto' }}>
          <div style={{ background: 'var(--primary)', padding: '0.75rem', borderRadius: '12px', display: 'flex', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4)' }}>
            <Book size={28} color="white" />
          </div>
          <div>
            <h2 style={{ fontSize: '1.8rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em', color: 'var(--text)' }}>
              Translation Memory & Glossary
            </h2>
            <p style={{ margin: '0.25rem 0 0', color: 'var(--text-muted)', fontSize: '0.95rem' }}>
              Enforce consistent translations for specific terms and character names.
            </p>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        
        {/* ADD ENTRY FORM */}
        <section style={{ background: 'var(--panel-bg)', borderRadius: '16px', padding: '1.5rem', border: '1px solid var(--panel-border)', boxShadow: '0 8px 24px rgba(0,0,0,0.2)' }}>
          <h3 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontSize: '1.1rem' }}>
            <Plus size={20} /> Add New Entry
          </h3>
          
          <form onSubmit={handleAdd} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr 2fr auto', gap: '1rem', alignItems: 'end' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Source Lang</label>
              <input
                type="text"
                value={sourceLang}
                onChange={e => setSourceLang(e.target.value)}
                className="text-input"
                placeholder="en"
                style={{ width: '100%' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Target Lang</label>
              <input
                type="text"
                value={targetLang}
                onChange={e => setTargetLang(e.target.value)}
                className="text-input"
                placeholder="de"
                style={{ width: '100%' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Source Term</label>
              <input
                type="text"
                value={sourceTerm}
                onChange={e => setSourceTerm(e.target.value)}
                className="text-input"
                placeholder="e.g. John Snow"
                style={{ width: '100%' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Target Term</label>
              <input
                type="text"
                value={targetTerm}
                onChange={e => setTargetTerm(e.target.value)}
                className="text-input"
                placeholder="e.g. Jon Schnee"
                style={{ width: '100%' }}
                required
              />
            </div>
            <button type="submit" className="btn-primary" style={{ padding: '0.75rem 1.25rem', height: '42px' }}>
              Add
            </button>
          </form>
          {status && <div style={{ marginTop: '1rem', color: 'var(--success)', fontSize: '0.9rem' }}>{status}</div>}
        </section>

        {/* GLOSSARY LIST */}
        <section style={{ background: 'var(--panel-bg)', borderRadius: '16px', padding: '1.5rem', border: '1px solid var(--panel-border)', boxShadow: '0 8px 24px rgba(0,0,0,0.2)' }}>
          <h3 style={{ margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text)', fontSize: '1.1rem' }}>
            <Globe size={20} /> Saved Entries
          </h3>

          {isLoading ? (
            <div style={{ color: 'var(--text-muted)' }}>Loading entries...</div>
          ) : entries.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
              No glossary entries found.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {entries.map(entry => (
                <div key={entry.id} style={{ 
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', 
                  padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px',
                  border: '1px solid rgba(255,255,255,0.05)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(0,0,0,0.2)', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      <span style={{ fontWeight: 'bold' }}>{entry.source_lang.toUpperCase()}</span>
                      <ArrowRight size={12} />
                      <span style={{ fontWeight: 'bold' }}>{entry.target_lang.toUpperCase()}</span>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
                      <span style={{ color: 'var(--text)', fontWeight: 500 }}>{entry.source_term}</span>
                      <ArrowRight size={16} color="var(--text-muted)" />
                      <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{entry.target_term}</span>
                    </div>
                  </div>
                  <button 
                    onClick={() => handleDelete(entry.id)} 
                    className="btn-danger" 
                    style={{ padding: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    title="Delete Entry"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
