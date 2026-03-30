import React, { useState, useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

export function ConsoleLog({ isOpen, setIsOpen }) {
  const [logs, setLogs] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;

    const eventSource = new EventSource('/api/console/stream');
    
    eventSource.onmessage = (event) => {
      // Decode the \n safe wrappers
      const msg = event.data.replace(/\\n/g, '\n');
      if (msg.trim()) {
        setLogs(prev => {
          const newLogs = [...prev, msg];
          if (newLogs.length > 300) return newLogs.slice(newLogs.length - 300);
          return newLogs;
        });
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [isOpen]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  return (
    <>
      {isOpen && (
        <div style={{
          position: 'fixed',
          bottom: '5rem',
          right: '2rem',
          width: '600px',
          maxWidth: '100%',
          height: '400px',
          background: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: '12px',
          zIndex: 999,
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 10px 30px rgba(0,0,0,0.8)',
          overflow: 'hidden'
        }}>
          <div style={{
            background: '#161b22',
            padding: '0.75rem 1rem',
            borderBottom: '1px solid #30363d',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Terminal size={16} color="#8b949e" />
            <h4 style={{ margin: 0, color: '#c9d1d9', fontSize: '0.9rem', fontFamily: 'monospace' }}>AutoSubs Console</h4>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
              <button 
                onClick={() => setLogs([])}
                style={{ background: 'transparent', border: '1px solid #30363d', color: '#c9d1d9', cursor: 'pointer', borderRadius: '4px', fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
              >
                Clear
              </button>
              <button 
                onClick={() => setIsOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>
          </div>
          <div 
            ref={scrollRef}
            style={{
              flex: 1,
              padding: '1rem',
              overflowY: 'auto',
              fontFamily: 'Consolas, monospace',
              fontSize: '0.85rem',
              color: '#c9d1d9',
              whiteSpace: 'pre-wrap',
              margin: 0
            }}
          >
            {logs.length === 0 ? (
              <span style={{ color: '#8b949e' }}>Awaiting terminal output...</span>
            ) : (
              logs.map((log, i) => <div key={i}>{log}</div>)
            )}
          </div>
        </div>
      )}
    </>
  );
}
