import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon, Shield, Server, Bell, Search,
  Globe, ArrowUp, ArrowDown, Check, X, Info,
  Cpu, Download, Database, RefreshCw, Trash2, Plus
} from 'lucide-react';
import { Modal } from './Modal';
import { FolderBrowser } from './FolderBrowser';
import { NetworkPathManager } from './NetworkPathManager';
import CustomSelect from './CustomSelect';

// ─── Unified design tokens ─────────────────────────────────────────────────────
const S = {
  // Outer wrapper
  page: {
    flex: 1,
    padding: '2rem',
    maxWidth: '900px',
    margin: '0 auto',
    width: '100%',
  },
  // Page-level header (gear + h2)
  pageHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '2rem',
  },
  pageTitle: {
    margin: 0,
    fontSize: '1.6rem',
    fontWeight: 700,
    letterSpacing: '-0.03em',
  },
  // Stack of sections
  stack: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  // Every section card — identical glass panel
  section: {
    background: 'rgba(255, 255, 255, 0.04)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '16px',
    padding: '1.5rem',
    boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
  },
  // Special tinted section (Native LLM)
  sectionTinted: {
    background: 'rgba(124, 102, 255, 0.06)',
    border: '1px solid rgba(124, 102, 255, 0.15)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    borderRadius: '16px',
    padding: '1.5rem',
    boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
  },
  // Section header row — ALWAYS: icon (20px, primary) + h3 — NO icon backgrounds
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
    marginBottom: '0.3rem',
  },
  sectionHeaderRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '0.3rem',
  },
  sectionHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
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
    margin: '0.3rem 0 1.25rem 0',
    lineHeight: 1.5,
  },
  // Form labels
  label: {
    display: 'block',
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '0.4rem',
  },
  // Inner card / sub-group within a section
  innerCard: {
    background: 'rgba(0,0,0,0.2)',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: '12px',
    padding: '1.25rem',
    marginBottom: '1rem',
  },
  // Sub-section divider
  subsectionTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
    fontSize: '0.8rem',
    fontWeight: 600,
    color: 'var(--primary)',
    marginBottom: '0.875rem',
  },
  // Model list item
  modelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: 'rgba(255,255,255,0.02)',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: '10px',
    padding: '0.875rem 1rem',
  },
};

export function Settings() {
  const [hfToken, setHfToken] = useState('');
  const [savingToken, setSavingToken] = useState(false);
  const [tokenStatus, setTokenStatus] = useState('');

  const [netConfig, setNetConfig] = useState({ share_path: '', username: '', password: '' });
  const [mounting, setMounting] = useState(false);
  const [mountStatus, setMountStatus] = useState('');
  const [networkMounts, setNetworkMounts] = useState({});

  const [discordWebhook, setDiscordWebhook] = useState('');
  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [modelCacheDir, setModelCacheDir] = useState('');
  const [savingNotifs, setSavingNotifs] = useState(false);
  const [notifStatus, setNotifStatus] = useState('');
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');

  const [providers, setProviders] = useState([]);
  const [expandedProvider, setExpandedProvider] = useState(null);

  const [localModels, setLocalModels] = useState([]);
  const [recommendedModels, setRecommendedModels] = useState([]);
  const [downloadingIds, setDownloadingIds] = useState(new Set());

  const [allModels, setAllModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [showWipeConfirm, setShowWipeConfirm] = useState(false);
  const [wipeConfirmText, setWipeConfirmText] = useState('');
  const [wiping, setWiping] = useState(false);

  const [customRepo, setCustomRepo] = useState('');
  const [repoFiles, setRepoFiles] = useState([]);
  const [scanningRepo, setScanningRepo] = useState(false);
  const [selectedFile, setSelectedFile] = useState('');

  // ─── Data loading ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/settings/hf-token')
      .then(r => r.ok && r.headers.get('content-type')?.includes('application/json') ? r.json() : Promise.reject())
      .then(d => { if (d?.token) setHfToken('*'.repeat(d.token.length)); })
      .catch(() => {});

    fetch('/api/config/settings')
      .then(r => r.ok && r.headers.get('content-type')?.includes('application/json') ? r.json() : Promise.reject())
      .then(d => {
        if (!d) return;
        setDiscordWebhook(d.discord_webhook || '');
        setTelegramToken(d.telegram_bot_token || '');
        setTelegramChatId(d.telegram_chat_id || '');
        setModelCacheDir(d.model_cache_dir || '');
        setProviders(d.subliminal_providers || []);
      }).catch(() => {});

    fetchLLMModels();
    fetchAllModels();
    fetchNetworkMounts();

    // One-time migration from legacy localStorage
    try {
      const legacy = JSON.parse(localStorage.getItem('as_network_shares') || '[]');
      if (legacy.length > 0) {
        legacy.forEach(share => {
          fetch('/api/settings/network-mount', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ share_path: share, username: '', password: '' })
          }).then(() => {
            const current = JSON.parse(localStorage.getItem('as_network_shares') || '[]');
            localStorage.setItem('as_network_shares', JSON.stringify(current.filter(s => s !== share)));
            fetchNetworkMounts();
          }).catch(console.error);
        });
      }
    } catch { /* ignored */ }
  }, []);

  // ─── Model download polling ───────────────────────────────────────────────
  useEffect(() => {
    if (downloadingIds.size === 0) return;
    const interval = setInterval(fetchLLMModels, 2000);
    return () => clearInterval(interval);
  }, [downloadingIds]);

  // ─── Fetchers ─────────────────────────────────────────────────────────────
  const fetchNetworkMounts = async () => {
    try {
      const resp = await fetch('/api/settings/network-mount');
      if (!resp.ok || !resp.headers.get('content-type')?.includes('application/json')) return;
      setNetworkMounts(await resp.json() || {});
    } catch (err) { console.error('Failed to fetch network mounts:', err); }
  };

  const fetchAllModels = async () => {
    setLoadingModels(true);
    try {
      const resp = await fetch('/api/models');
      if (!resp.ok || !resp.headers.get('content-type')?.includes('application/json')) return;
      setAllModels(await resp.json() || []);
    } catch (err) { console.error('Failed to fetch all models:', err); }
    finally { setLoadingModels(false); }
  };

  const fetchLLMModels = async () => {
    try {
      const resp = await fetch('/api/llm/models');
      if (!resp.ok || !resp.headers.get('content-type')?.includes('application/json')) return;
      const data = await resp.json();
      if (!data) return;
      setLocalModels(data.local || []);
      setRecommendedModels(data.recommended || []);
      const downloading = new Set();
      data.recommended?.forEach(m => { if (m.progress > 0 && m.progress < 100) downloading.add(m.id); });
      setDownloadingIds(downloading);
    } catch (err) { console.error('Failed to fetch LLM models:', err); }
  };

  // ─── Handlers ─────────────────────────────────────────────────────────────
  const showSaved = (msg) => { setSavedMessage(msg); setTimeout(() => setSavedMessage(''), 3000); };

  const handleSaveToken = async () => {
    setSavingToken(true); setTokenStatus('');
    try {
      const resp = await fetch('/api/settings/hf-token', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: hfToken })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Failed to save token');
      showSaved(data.message);
    } catch (err) { setTokenStatus(`Error: ${err.message}`); }
    finally { setSavingToken(false); }
  };

  const handleMountNetwork = async (cfg) => {
    setMounting(true); setMountStatus('');
    try {
      const resp = await fetch('/api/settings/network-mount', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Failed to mount network');
      showSaved(data.message);
      fetchNetworkMounts();
      return data;
    } catch (err) { setMountStatus(`Error: ${err.message}`); throw err; }
    finally { setMounting(false); }
  };

  const handleRefreshMount = async (path) => {
    try {
      const resp = await fetch(`/api/settings/network-mount/check?share_path=${encodeURIComponent(path)}`);
      if (resp.ok) {
        const data = await resp.json();
        setNetworkMounts(prev => ({ ...prev, [path]: { ...prev[path], online: data.online } }));
      }
    } catch (err) { console.error('Checking status failed:', err); }
  };

  const handleUnmountNetwork = async (path) => {
    if (!window.confirm(`Disconnect from ${path}?`)) return;
    try {
      const resp = await fetch(`/api/settings/network-mount?share_path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      if (resp.ok) fetchNetworkMounts();
    } catch (err) { console.error('Failed to unmount:', err); }
  };

  const handleSaveNotifications = async () => {
    setSavingNotifs(true); setNotifStatus('');
    try {
      const resp = await fetch('/api/config/settings', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          discord_webhook: discordWebhook,
          telegram_bot_token: telegramToken,
          telegram_chat_id: telegramChatId,
          model_cache_dir: modelCacheDir,
          subliminal_providers: providers,
        })
      });
      if (!resp.ok) throw new Error('Failed to save settings');
      showSaved('Settings saved successfully!');
    } catch (err) { setNotifStatus(`Error: ${err.message}`); }
    finally { setSavingNotifs(false); }
  };

  const handleDownloadModel = async (modelId) => {
    try {
      const resp = await fetch('/api/llm/download', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId })
      });
      if (resp.ok) { setDownloadingIds(prev => new Set([...prev, modelId])); fetchLLMModels(); }
    } catch (err) { console.error('Failed to start download:', err); }
  };

  const handleScanRepo = async () => {
    setScanningRepo(true); setRepoFiles([]); setSelectedFile('');
    try {
      const resp = await fetch(`/api/llm/scan?repo_id=${encodeURIComponent(customRepo)}`);
      const data = await resp.json();
      if (resp.ok) {
        setRepoFiles(data.files || []);
        if (!data.files?.length) alert('No .gguf files found in this repository.');
      } else { alert(data.detail || 'Failed to scan repository.'); }
    } catch { alert('Failed to reach server for scanning.'); }
    finally { setScanningRepo(false); }
  };

  const handleRegisterAndDownload = async () => {
    try {
      const regResp = await fetch('/api/llm/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo: customRepo, file: selectedFile, name: `Custom: ${selectedFile.split('/').pop()}` })
      });
      const regData = await regResp.json();
      if (!regResp.ok) throw new Error(regData.detail || 'Registration failed');
      await handleDownloadModel(regData.model_id);
      setRepoFiles([]); setCustomRepo(''); setSelectedFile('');
    } catch (err) { alert(err.message); }
  };

  const handleDeleteModel = async (path) => {
    if (!window.confirm(`Delete model?\n${path.split(/[\\/]/).pop()}`)) return;
    try {
      const resp = await fetch(`/api/models?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      if (resp.ok) { fetchAllModels(); fetchLLMModels(); }
    } catch (err) { console.error('Failed to delete model:', err); }
  };

  const handleWipeModels = async () => {
    if (wipeConfirmText !== 'DELETE') return;
    setWiping(true);
    try {
      const resp = await fetch('/api/models/wipe', { method: 'POST' });
      if (resp.ok) {
        setShowWipeConfirm(false); setWipeConfirmText('');
        fetchAllModels(); fetchLLMModels();
        alert('Model cache wiped successfully.');
      }
    } catch { alert('Failed to wipe models.'); }
    finally { setWiping(false); }
  };

  const moveProvider = (index, direction) => {
    const arr = [...providers];
    const target = index + direction;
    if (target < 0 || target >= arr.length) return;
    const [moved] = arr.splice(index, 1);
    arr.splice(target, 0, moved);
    setProviders(arr);
  };

  const moveProviderToExtreme = (index, toTop) => {
    const arr = [...providers];
    const [moved] = arr.splice(index, 1);
    toTop ? arr.unshift(moved) : arr.push(moved);
    setProviders(arr);
  };

  const toggleProvider = (index) => {
    const arr = [...providers];
    const isActive = !arr[index].active;
    arr[index].active = isActive;
    if (!isActive) { const [moved] = arr.splice(index, 1); arr.push(moved); }
    setProviders(arr);
  };

  const updateProviderCreds = (index, field, value) => {
    const arr = [...providers]; arr[index][field] = value; setProviders(arr);
  };

  // ─── Type badge colour map ────────────────────────────────────────────────
  const typeBadgeColor = (type) => {
    if (type === 'whisper') return { bg: 'rgba(59,130,246,0.15)', color: '#7cb9ff' };
    if (type === 'nllb') return { bg: 'rgba(74,222,128,0.12)', color: '#6be4a0' };
    if (type === 'gguf') return { bg: 'rgba(168,85,247,0.15)', color: '#c084fc' };
    return { bg: 'rgba(255,255,255,0.07)', color: 'var(--text-muted)' };
  };

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div style={S.page}>

      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div style={S.pageHeader}>
        <SettingsIcon size={28} color="var(--primary)" />
        <h2 style={S.pageTitle}>Application Settings</h2>
      </div>

      {/* ── Toast Notification ───────────────────────────────────────────── */}
      {savedMessage && (
        <div style={{
          position: 'fixed', top: '1.5rem', right: '1.5rem', zIndex: 9999,
          background: 'var(--success)', color: '#fff', padding: '0.75rem 1.25rem',
          borderRadius: '12px', fontWeight: 600, boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', gap: '0.5rem', animation: 'fadeIn 0.2s ease-out',
          border: '1px solid rgba(255,255,255,0.12)',
        }}>
          <Check size={16} /> {savedMessage}
        </div>
      )}

      <div style={S.stack}>

        {/* ════════════════════════════════════════════════════════════════
            1. HUGGINGFACE AUTHENTICATION
        ════════════════════════════════════════════════════════════════ */}
        <section style={S.section}>
          <div style={S.sectionHeader}>
            <Shield size={20} color="var(--primary)" />
            <h3 style={S.sectionTitle}>HuggingFace Authentication</h3>
          </div>
          <p style={S.sectionDesc}>
            Provide a HuggingFace Read token to bypass unauthenticated IP rate-limits and speed up model downloads.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <input
              type="password"
              placeholder="hf_..."
              value={hfToken}
              onChange={(e) => setHfToken(e.target.value)}
              className="text-input"
              style={{ flex: 1 }}
            />
            <button className="btn-primary" onClick={handleSaveToken} disabled={savingToken}>
              {savingToken ? 'Authenticating...' : 'Save & Auth'}
            </button>
          </div>
          {tokenStatus && (
            <div style={{ marginTop: '0.6rem', fontSize: '0.82rem', color: tokenStatus.startsWith('Error') ? 'var(--danger)' : 'var(--success)' }}>
              {tokenStatus}
            </div>
          )}
        </section>

        {/* ════════════════════════════════════════════════════════════════
            2. NETWORK PATH MANAGER
        ════════════════════════════════════════════════════════════════ */}
        <NetworkPathManager
          networkMounts={networkMounts}
          onMount={handleMountNetwork}
          onUnmount={handleUnmountNetwork}
          onRefresh={handleRefreshMount}
        />

        {/* ════════════════════════════════════════════════════════════════
            3. ALERT & NOTIFICATION INTEGRATION
        ════════════════════════════════════════════════════════════════ */}
        <section style={S.section}>
          <div style={S.sectionHeader}>
            <Bell size={20} color="var(--primary)" />
            <h3 style={S.sectionTitle}>Alert &amp; Notification Integration</h3>
          </div>
          <p style={S.sectionDesc}>
            Receive push notifications when jobs complete or fail. Windows triggers Desktop Notifications automatically.
            Configure these for remote server deployments.
          </p>

          <div style={{ marginBottom: '0.875rem' }}>
            <label style={S.label}>Discord Webhook URL</label>
            <input
              type="text"
              placeholder="https://discord.com/api/webhooks/..."
              value={discordWebhook}
              onChange={e => setDiscordWebhook(e.target.value)}
              className="text-input"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.875rem', marginBottom: '1.25rem' }}>
            <div>
              <label style={S.label}>Telegram Bot Token</label>
              <input
                type="text"
                placeholder="123456:ABC-DEF1234gh..."
                value={telegramToken}
                onChange={e => setTelegramToken(e.target.value)}
                className="text-input"
              />
            </div>
            <div>
              <label style={S.label}>Telegram Chat ID</label>
              <input
                type="text"
                placeholder="-1001234567890"
                value={telegramChatId}
                onChange={e => setTelegramChatId(e.target.value)}
                className="text-input"
              />
            </div>
          </div>

          <button className="btn-primary" onClick={handleSaveNotifications} disabled={savingNotifs}>
            {savingNotifs ? 'Saving...' : 'Save Notification Settings'}
          </button>
          {notifStatus && (
            <div style={{ marginTop: '0.6rem', fontSize: '0.82rem', color: notifStatus.startsWith('Error') ? 'var(--danger)' : 'var(--success)' }}>
              {notifStatus}
            </div>
          )}
        </section>

        {/* ════════════════════════════════════════════════════════════════
            4. STORAGE & MODELS
        ════════════════════════════════════════════════════════════════ */}
        <section style={S.section}>
          <div style={S.sectionHeader}>
            <Server size={20} color="var(--primary)" />
            <h3 style={S.sectionTitle}>Storage &amp; Models</h3>
          </div>
          <p style={S.sectionDesc}>
            Redirect large AI model downloads (Whisper, WhisperX, HuggingFace) to a specific directory.
            Leave empty to use the default <code style={{ fontSize: '0.8rem', background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: '4px' }}>backend/models/</code> folder.
          </p>

          <div style={{ marginBottom: '1rem' }}>
            <label style={S.label}>Model Cache Directory</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                className="text-input"
                placeholder="E:\AI_Models"
                value={modelCacheDir}
                onChange={(e) => setModelCacheDir(e.target.value)}
                style={{ flex: 1 }}
              />
              <button
                onClick={() => setIsPickerOpen(true)}
                style={{
                  padding: '0 1rem',
                  display: 'flex', alignItems: 'center', gap: '0.4rem',
                  whiteSpace: 'nowrap',
                }}
              >
                <Search size={15} /> Browse
              </button>
            </div>
          </div>

          <button className="btn-primary" onClick={handleSaveNotifications} disabled={savingNotifs}>
            {savingNotifs ? 'Saving...' : 'Save Storage Settings'}
          </button>
        </section>

        {/* ════════════════════════════════════════════════════════════════
            5. NATIVE LLM (llama-cpp-python)
        ════════════════════════════════════════════════════════════════ */}
        <section style={S.sectionTinted}>
          <div style={S.sectionHeader}>
            <Cpu size={20} color="var(--primary)" />
            <h3 style={S.sectionTitle}>Native LLM (llama-cpp-python)</h3>
          </div>
          <p style={S.sectionDesc}>
            AutoSubs AI uses an <strong>in-process</strong> Native LLM for state-of-the-art translations.
            No external installation required. Models are stored in your configured cache directory.
          </p>

          {/* Recommended Models */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={S.subsectionTitle}>
              <Download size={14} /> Recommended &amp; Custom Models
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {recommendedModels.map(model => (
                <div key={model.id} style={{
                  ...S.modelRow,
                  borderLeft: model.is_custom ? '2px solid var(--primary)' : '1px solid rgba(255,255,255,0.05)',
                }}>
                  <div style={{ flex: 1, minWidth: 0, marginRight: '1rem' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {model.name}
                      <span style={{ fontWeight: 400, fontSize: '0.78rem', color: 'var(--text-muted)' }}>({model.size})</span>
                      {model.is_custom && (
                        <span style={{ fontSize: '0.68rem', background: 'rgba(124,102,255,0.18)', color: 'var(--primary)', padding: '1px 6px', borderRadius: '4px', fontWeight: 700 }}>CUSTOM</span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>{model.description}</div>
                    {model.progress > 0 && model.progress < 100 && (
                      <div style={{ marginTop: '0.5rem', height: '3px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${model.progress}%`, background: 'var(--primary)', transition: 'width 0.3s ease' }} />
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => !model.is_downloaded && handleDownloadModel(model.id)}
                    disabled={model.is_downloaded || downloadingIds.has(model.id)}
                    style={{
                      flexShrink: 0,
                      padding: '0.4rem 1rem',
                      borderRadius: '8px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      border: 'none',
                      cursor: model.is_downloaded ? 'default' : 'pointer',
                      display: 'flex', alignItems: 'center', gap: '0.35rem',
                      background: model.is_downloaded ? 'rgba(74,222,128,0.12)' : 'var(--primary)',
                      color: model.is_downloaded ? 'var(--success)' : '#fff',
                      opacity: downloadingIds.has(model.id) ? 0.7 : 1,
                      transition: 'all 0.2s',
                    }}
                  >
                    {model.is_downloaded ? <><Check size={13} /> Downloaded</> :
                     downloadingIds.has(model.id) ? 'Downloading...' : 'Download'}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Custom Model Registration */}
          <div style={S.innerCard}>
            <div style={{ ...S.subsectionTitle, color: 'var(--text-muted)' }}>
              <Globe size={13} /> Download Custom GGUF from HuggingFace
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.875rem' }}>
              <input
                type="text"
                className="text-input"
                placeholder="e.g. bartowski/Qwen_Qwen3.5-9B-GGUF"
                value={customRepo}
                onChange={(e) => setCustomRepo(e.target.value)}
                style={{ flex: 1 }}
              />
              <button
                onClick={handleScanRepo}
                disabled={scanningRepo || !customRepo}
                style={{
                  background: 'transparent', border: '1px solid rgba(255,255,255,0.12)',
                  color: 'var(--text-muted)', padding: '0 1rem', borderRadius: '8px',
                  display: 'flex', alignItems: 'center', gap: '0.4rem',
                  cursor: scanningRepo || !customRepo ? 'not-allowed' : 'pointer',
                  fontSize: '0.875rem', whiteSpace: 'nowrap', transition: 'all 0.2s',
                  opacity: scanningRepo || !customRepo ? 0.5 : 1,
                }}
              >
                {scanningRepo ? 'Scanning...' : 'Scan Repo'}
              </button>
            </div>
            {repoFiles.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', animation: 'fadeIn 0.3s ease' }}>
                <CustomSelect
                  value={selectedFile}
                  onChange={(e) => setSelectedFile(e.target.value)}
                  placeholder="-- Select .gguf file --"
                  options={repoFiles.map(f => ({ value: f, label: f }))}
                />
                <button
                  className="btn-primary"
                  onClick={handleRegisterAndDownload}
                  disabled={!selectedFile}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  Add &amp; Download
                </button>
              </div>
            )}
          </div>
        </section>

        {/* ════════════════════════════════════════════════════════════════
            6. MODEL CACHE MANAGEMENT
        ════════════════════════════════════════════════════════════════ */}
        <section style={S.section}>
          <div style={S.sectionHeaderRow}>
            <div style={S.sectionHeaderLeft}>
              <Database size={20} color="var(--primary)" />
              <h3 style={S.sectionTitle}>Model Cache Management</h3>
            </div>
            <button
              onClick={() => setShowWipeConfirm(true)}
              style={{
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.2)',
                color: 'var(--danger)',
                padding: '0.4rem 0.875rem',
                borderRadius: '8px',
                fontSize: '0.8rem',
                fontWeight: 600,
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                cursor: 'pointer', transition: 'all 0.2s',
              }}
            >
              <Trash2 size={14} /> Wipe Cache
            </button>
          </div>
          <p style={S.sectionDesc}>View and manage downloaded AI weights (Whisper, NLLB, GGUF).</p>

          {loadingModels ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2.5rem' }}>
              <RefreshCw size={28} color="var(--primary)" style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          ) : allModels.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
              {allModels.map((model) => {
                const badge = typeBadgeColor(model.type);
                return (
                  <div
                    key={model.path}
                    className="model-cache-card"
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '12px', padding: '1rem',
                      display: 'flex', flexDirection: 'column', gap: '0.5rem',
                      position: 'relative', transition: 'border-color 0.2s',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{
                        fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                        background: badge.bg, color: badge.color, padding: '2px 7px', borderRadius: '5px',
                      }}>{model.type}</span>
                      <button
                        onClick={() => handleDeleteModel(model.path)}
                        title="Delete model"
                        style={{
                          background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.25)',
                          cursor: 'pointer', padding: '2px', display: 'flex', alignItems: 'center',
                          borderRadius: '4px', transition: 'color 0.2s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                        onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.25)'}
                      >
                        <X size={14} />
                      </button>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={model.name}>
                      {model.name}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      <span>{model.size}</span>
                      <span style={{ maxWidth: '55%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontStyle: 'italic' }} title={model.path.split(/[\\/]/).pop()}>
                        {model.path.split(/[\\/]/).pop()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{
              textAlign: 'center', padding: '2.5rem',
              background: 'rgba(0,0,0,0.15)', border: '1px dashed rgba(255,255,255,0.07)', borderRadius: '12px',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem',
            }}>
              <Database size={36} color="rgba(255,255,255,0.1)" />
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>No downloaded models found in the current cache directory.</p>
            </div>
          )}
        </section>

        {/* ════════════════════════════════════════════════════════════════
            7. SUBTITLE DISCOVERY PROVIDERS
        ════════════════════════════════════════════════════════════════ */}
        <section style={S.section}>
          <div style={S.sectionHeader}>
            <Globe size={20} color="var(--primary)" />
            <h3 style={S.sectionTitle}>Subtitle Discovery Providers</h3>
          </div>
          <p style={S.sectionDesc}>
            Configure and prioritize subtitle sources. Drag to reorder. Credentials required for some providers.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginBottom: '1.25rem' }}>
            {providers.map((p, idx) => {
              const needsCreds = p.id.includes('opensubtitles') || p.id === 'addic7ed' || p.id === 'subsource' || p.id === 'subdl';
              const isExpanded = expandedProvider === p.id;
              return (
                <div key={p.id}>
                  {/* ── Compact provider row ── */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 0.75rem',
                    background: isExpanded ? 'rgba(124,102,255,0.06)' : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${isExpanded ? 'rgba(124,102,255,0.18)' : 'rgba(255,255,255,0.05)'}`,
                    borderRadius: isExpanded ? '10px 10px 0 0' : '10px',
                    opacity: p.active ? 1 : 0.5,
                    transition: 'all 0.15s',
                  }}>
                    {/* Rank number */}
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 700, color: 'rgba(255,255,255,0.2)',
                      width: '1.1rem', textAlign: 'center', flexShrink: 0,
                    }}>{idx + 1}</span>

                    {/* ↑↓ move buttons — compact */}
                    <div style={{ display: 'flex', gap: '2px', flexShrink: 0 }}>
                      <button onClick={() => moveProvider(idx, -1)} disabled={idx === 0} title="Move up"
                        style={{
                          background: 'transparent', border: '1px solid rgba(255,255,255,0.07)',
                          color: idx === 0 ? 'rgba(255,255,255,0.1)' : 'var(--text-muted)',
                          padding: '2px 5px', borderRadius: '4px', cursor: idx === 0 ? 'default' : 'pointer',
                          display: 'flex', alignItems: 'center', lineHeight: 1, transition: 'all 0.15s',
                        }}>
                        <ArrowUp size={11} />
                      </button>
                      <button onClick={() => moveProvider(idx, 1)} disabled={idx === providers.length - 1} title="Move down"
                        style={{
                          background: 'transparent', border: '1px solid rgba(255,255,255,0.07)',
                          color: idx === providers.length - 1 ? 'rgba(255,255,255,0.1)' : 'var(--text-muted)',
                          padding: '2px 5px', borderRadius: '4px', cursor: idx === providers.length - 1 ? 'default' : 'pointer',
                          display: 'flex', alignItems: 'center', lineHeight: 1, transition: 'all 0.15s',
                        }}>
                        <ArrowDown size={11} />
                      </button>
                    </div>

                    {/* Provider name */}
                    <span style={{ flex: 1, fontWeight: 600, fontSize: '0.875rem', textTransform: 'capitalize' }}>{p.id}</span>

                    {/* Status chip */}
                    <span style={{
                      fontSize: '0.62rem', fontWeight: 700, padding: '1px 6px', borderRadius: '999px',
                      background: p.active ? 'rgba(74,222,128,0.1)' : 'rgba(255,255,255,0.05)',
                      color: p.active ? 'var(--success)' : 'var(--text-muted)',
                      letterSpacing: '0.04em',
                    }}>{p.active ? 'ON' : 'OFF'}</span>

                    {/* Credentials expand button (only if provider needs them) */}
                    {needsCreds && p.active && (
                      <button
                        onClick={() => setExpandedProvider(isExpanded ? null : p.id)}
                        title="Configure credentials"
                        style={{
                          background: isExpanded ? 'rgba(124,102,255,0.15)' : 'transparent',
                          border: `1px solid ${isExpanded ? 'rgba(124,102,255,0.3)' : 'rgba(255,255,255,0.08)'}`,
                          color: isExpanded ? 'var(--primary)' : 'var(--text-muted)',
                          padding: '3px 7px', borderRadius: '5px', cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: '3px',
                          fontSize: '0.7rem', fontWeight: 600, transition: 'all 0.15s',
                        }}
                      >
                        <Info size={11} />Key
                      </button>
                    )}

                    {/* Enable/Disable toggle */}
                    <button
                      onClick={() => toggleProvider(idx)}
                      title={p.active ? 'Disable' : 'Enable'}
                      style={{
                        background: p.active ? 'rgba(239,68,68,0.08)' : 'rgba(74,222,128,0.08)',
                        border: `1px solid ${p.active ? 'rgba(239,68,68,0.18)' : 'rgba(74,222,128,0.18)'}`,
                        color: p.active ? 'var(--danger)' : 'var(--success)',
                        padding: '3px 7px', borderRadius: '5px', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', lineHeight: 1, transition: 'all 0.15s',
                      }}
                    >
                      {p.active ? <X size={13} /> : <Check size={13} />}
                    </button>
                  </div>

                  {/* ── Credentials panel (collapsible) ── */}
                  {isExpanded && needsCreds && (
                    <div style={{
                      display: 'flex', flexWrap: 'wrap', gap: '0.6rem',
                      padding: '0.875rem 0.875rem 1rem',
                      background: 'rgba(0,0,0,0.25)',
                      border: '1px solid rgba(124,102,255,0.12)',
                      borderTop: 'none',
                      borderRadius: '0 0 10px 10px',
                      animation: 'fadeIn 0.15s ease-out',
                    }}>
                      {(p.id !== 'subsource' && p.id !== 'subdl') && (
                        <>
                          <div style={{ flex: '1 1 160px' }}>
                            <label style={S.label}>Username</label>
                            <input type="text" placeholder="Username" className="text-input"
                              value={p.user || ''} onChange={e => updateProviderCreds(idx, 'user', e.target.value)} />
                          </div>
                          <div style={{ flex: '1 1 160px' }}>
                            <label style={S.label}>Password</label>
                            <input type="password" placeholder="Password" className="text-input"
                              value={p.pass || ''} onChange={e => updateProviderCreds(idx, 'pass', e.target.value)} />
                          </div>
                        </>
                      )}
                      {(p.id === 'opensubtitlescom' || p.id === 'subsource' || p.id === 'subdl') && (
                        <div style={{ flex: '1 1 100%' }}>
                          <label style={S.label}>API Key</label>
                          <input type="password" placeholder={`API key from ${p.id}`} className="text-input"
                            value={p.api_key || ''} onChange={e => updateProviderCreds(idx, 'api_key', e.target.value)} />
                          <p style={{ margin: '0.35rem 0 0', fontSize: '0.72rem', color: 'rgba(124,102,255,0.75)', display: 'flex', alignItems: 'center', gap: '3px' }}>
                            <Info size={10} style={{ flexShrink: 0 }} />
                            {p.id === 'subdl' ? <>Generate at <strong>subdl.com</strong> → Account → API Key</> :
                             p.id === 'subsource' ? <>Generate at <strong>subsource.net</strong> → Profile → My Profile</> :
                             <>Register at <strong>opensubtitles.com</strong> to get your Consumer Key</>}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <button className="btn-primary" onClick={handleSaveNotifications} disabled={savingNotifs}>
            {savingNotifs ? 'Saving...' : 'Save Provider Priority & Settings'}
          </button>
        </section>

        {/* Bottom spacer */}
        <div style={{ height: '4rem' }} />
      </div>

      {/* ── Modals ───────────────────────────────────────────────────────── */}
      <Modal isOpen={isPickerOpen} onClose={() => setIsPickerOpen(false)} title="Select Model Storage Directory">
        <FolderBrowser onSelect={setModelCacheDir} selectedPath={modelCacheDir} />
      </Modal>

      {showWipeConfirm && (
        <Modal isOpen={true} title="Clear All Models?" onClose={() => { setShowWipeConfirm(false); setWipeConfirmText(''); }}>
          <div style={{ padding: '0.25rem' }}>
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: '1rem', padding: '1rem',
              background: 'rgba(239,68,68,0.08)', borderRadius: '10px', border: '1px solid rgba(239,68,68,0.18)', marginBottom: '1.5rem',
            }}>
              <Shield size={20} color="var(--danger)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <h3 style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: '0.3rem', fontSize: '0.95rem' }}>Danger Zone</h3>
                <p style={{ fontSize: '0.85rem', color: 'rgba(239,68,68,0.8)', margin: 0, lineHeight: 1.5 }}>
                  This will delete <strong>ALL</strong> downloaded AI models, weights, and caches. You will need to re-download them before transcribing or translating again.
                </p>
              </div>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ ...S.label, marginBottom: '0.5rem' }}>
                Please type <span style={{ color: 'var(--text-main)', fontWeight: 700, background: 'rgba(255,255,255,0.08)', padding: '1px 6px', borderRadius: '4px' }}>DELETE</span> to confirm
              </label>
              <input
                type="text"
                value={wipeConfirmText}
                onChange={(e) => setWipeConfirmText(e.target.value)}
                autoFocus
                className="text-input"
                placeholder="Type 'DELETE' here..."
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setShowWipeConfirm(false); setWipeConfirmText(''); }}
                style={{
                  background: 'transparent', border: 'none', color: 'var(--text-muted)',
                  padding: '0.5rem 1rem', cursor: 'pointer', fontSize: '0.875rem', borderRadius: '8px',
                  transition: 'color 0.2s',
                }}
              >
                Cancel
              </button>
              <button
                disabled={wipeConfirmText !== 'DELETE' || wiping}
                onClick={handleWipeModels}
                style={{
                  padding: '0.5rem 1.5rem', borderRadius: '8px', fontSize: '0.875rem', fontWeight: 700,
                  border: 'none', cursor: wipeConfirmText === 'DELETE' && !wiping ? 'pointer' : 'not-allowed',
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  background: wipeConfirmText === 'DELETE' && !wiping ? 'var(--danger)' : 'rgba(255,255,255,0.06)',
                  color: wipeConfirmText === 'DELETE' && !wiping ? '#fff' : 'var(--text-muted)',
                  transition: 'all 0.2s',
                  boxShadow: wipeConfirmText === 'DELETE' && !wiping ? '0 4px 20px rgba(239,68,68,0.25)' : 'none',
                }}
              >
                {wiping ? (
                  <><RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> Wiping...</>
                ) : (
                  <><Trash2 size={15} /> Wipe All Models</>
                )}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
