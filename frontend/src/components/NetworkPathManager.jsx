import React, { useState } from 'react';
import { Server, Database, Plus, Trash2, Wifi, WifiOff, RefreshCw, Info } from 'lucide-react';

// ─── Shared section-level styles (consistent with Settings.jsx) ────────────────
const S = {
  section: {
    background: 'rgba(255, 255, 255, 0.04)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '1.5rem',
    boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
    marginBottom: '0.4rem',
  },
  sectionTitle: {
    margin: 0,
    fontSize: '1.05rem',
    fontWeight: 600,
    letterSpacing: '-0.01em',
    color: 'var(--text-main)',
  },
  sectionDesc: {
    color: 'var(--text-muted)',
    fontSize: '0.875rem',
    marginBottom: '1.25rem',
    marginTop: '0.25rem',
    lineHeight: 1.5,
  },
  label: {
    display: 'block',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '0.375rem',
  },
  fieldGroup: {
    background: 'rgba(0,0,0,0.25)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: '12px',
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.875rem',
    marginBottom: '1rem',
  },
  subheader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '0.75rem',
  },
  subheaderTitle: {
    fontSize: '0.7rem',
    fontWeight: 700,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
  },
  badge: {
    fontSize: '0.65rem',
    background: 'rgba(0,0,0,0.3)',
    color: 'var(--text-muted)',
    padding: '2px 8px',
    borderRadius: '999px',
    border: '1px solid rgba(255,255,255,0.06)',
  },
};

export function NetworkPathManager({ networkMounts, onMount, onUnmount, onRefresh }) {
  const [netConfig, setNetConfig] = useState({ share_path: '', username: '', password: '' });
  const [mounting, setMounting] = useState(false);
  const [mountStatus, setMountStatus] = useState('');
  const [checkingPath, setCheckingPath] = useState(null);

  const handleMount = async () => {
    setMounting(true);
    setMountStatus('');
    try {
      await onMount(netConfig);
      setNetConfig({ share_path: '', username: '', password: '' });
    } catch (err) {
      setMountStatus(`Error: ${err.message}`);
    } finally {
      setMounting(false);
    }
  };

  const handleCheckStatus = async (path) => {
    setCheckingPath(path);
    try {
      await onRefresh(path);
    } finally {
      setCheckingPath(null);
    }
  };

  const mountCount = Object.keys(networkMounts || {}).length;

  return (
    <section style={S.section}>
      {/* ── Section Header ─────────────────────────────────────────── */}
      <div style={S.sectionHeader}>
        <Server size={20} color="var(--primary)" />
        <h3 style={S.sectionTitle}>Network Path Manager (SMB/NFS)</h3>
      </div>
      <p style={S.sectionDesc}>
        Authenticate and map network shares for full permission access. Shares are registered in the backend and
        persist across browser sessions.
      </p>

      {/* ── Mount Form ─────────────────────────────────────────────── */}
      <div style={S.fieldGroup}>
        <div>
          <label style={S.label}>Network Path / Share</label>
          <input
            type="text"
            value={netConfig.share_path}
            onChange={(e) => setNetConfig({ ...netConfig, share_path: e.target.value })}
            placeholder="\\192.168.1.100\movies  OR  /mnt/nas/media"
            className="text-input"
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.875rem' }}>
          <div>
            <label style={S.label}>Username (Optional)</label>
            <input
              type="text"
              value={netConfig.username}
              onChange={(e) => setNetConfig({ ...netConfig, username: e.target.value })}
              placeholder="Guest"
              className="text-input"
            />
          </div>
          <div>
            <label style={S.label}>Password (Optional)</label>
            <input
              type="password"
              value={netConfig.password}
              onChange={(e) => setNetConfig({ ...netConfig, password: e.target.value })}
              placeholder="••••••••"
              className="text-input"
            />
          </div>
        </div>

        <button
          className="btn-primary"
          onClick={handleMount}
          disabled={mounting || !netConfig.share_path.trim()}
          style={{ alignSelf: 'flex-start' }}
        >
          {mounting ? (
            <>
              <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
              Mapping Share...
            </>
          ) : (
            <>
              <Plus size={15} />
              Authenticate &amp; Mount Path
            </>
          )}
        </button>

        {mountStatus && (
          <div style={{
            fontSize: '0.8rem',
            padding: '0.6rem 0.875rem',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: mountStatus.startsWith('Error') ? 'rgba(239,68,68,0.08)' : 'rgba(74,222,128,0.08)',
            border: `1px solid ${mountStatus.startsWith('Error') ? 'rgba(239,68,68,0.2)' : 'rgba(74,222,128,0.2)'}`,
            color: mountStatus.startsWith('Error') ? 'var(--danger)' : 'var(--success)',
          }}>
            <Info size={14} />
            {mountStatus}
          </div>
        )}
      </div>

      {/* ── Mapped Shares List ─────────────────────────────────────── */}
      <div style={S.subheader}>
        <span style={S.subheaderTitle}>Currently Mapped Shares</span>
        <span style={S.badge}>{mountCount} Total</span>
      </div>

      {mountCount > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {Object.entries(networkMounts).map(([path, info]) => (
            <div
              key={path}
              className="share-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '10px',
                padding: '0.75rem 1rem',
                transition: 'border-color 0.2s',
              }}
            >
              {/* Status & Info */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', minWidth: 0 }}>
                <div style={{ position: 'relative', flexShrink: 0 }}>
                  <Database size={18} color={info.online ? 'var(--success)' : 'var(--danger)'} />
                  <span style={{
                    position: 'absolute',
                    bottom: -3,
                    right: -3,
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: info.online ? 'var(--success)' : 'var(--danger)',
                    border: '1.5px solid var(--bg-color)',
                    boxShadow: info.online ? '0 0 6px var(--success)' : '0 0 6px var(--danger)',
                  }} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={path}>
                    {path}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.2rem', fontSize: '0.7rem', color: 'var(--text-muted)', alignItems: 'center' }}>
                    <span style={{ background: 'rgba(255,255,255,0.06)', padding: '1px 6px', borderRadius: '4px' }}>
                      {info.username ? `User: ${info.username}` : 'Guest Access'}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: info.online ? 'var(--success)' : 'var(--danger)' }}>
                      {info.online ? <Wifi size={10} /> : <WifiOff size={10} />}
                      {info.online ? 'Reachable' : 'Unreachable'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '0.25rem', flexShrink: 0 }}>
                <button
                  onClick={() => handleCheckStatus(path)}
                  disabled={checkingPath === path}
                  title="Check Connectivity"
                  style={{
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: 'var(--text-muted)',
                    padding: '0.35rem',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  <RefreshCw size={14} style={{ animation: checkingPath === path ? 'spin 1s linear infinite' : 'none' }} />
                </button>
                <button
                  onClick={() => onUnmount(path)}
                  title="Disconnect Share"
                  style={{
                    background: 'transparent',
                    border: '1px solid rgba(255,255,255,0.08)',
                    color: 'var(--text-muted)',
                    padding: '0.35rem',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          background: 'rgba(0,0,0,0.15)',
          border: '1px dashed rgba(255,255,255,0.08)',
          borderRadius: '10px',
          gap: '0.5rem',
        }}>
          <WifiOff size={24} color="rgba(255,255,255,0.15)" />
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>No network shares currently mapped.</p>
        </div>
      )}
    </section>
  );
}
