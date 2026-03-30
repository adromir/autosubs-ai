import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Shield, Server, Bell, Search, Globe, ArrowUp, ArrowDown, Check, X, Info, ChevronsUp, ChevronsDown, Cpu, Download, Database } from 'lucide-react';
import { Modal } from './Modal';
import { FolderBrowser } from './FolderBrowser';

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
  
  const [localModels, setLocalModels] = useState([]);
  const [recommendedModels, setRecommendedModels] = useState([]);
  const [downloadingIds, setDownloadingIds] = useState(new Set());
  
  const [allModels, setAllModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [showWipeConfirm, setShowWipeConfirm] = useState(false);
  const [wipeConfirmText, setWipeConfirmText] = useState('');
  const [wiping, setWiping] = useState(false);

  // Custom Model Scanning State
  const [customRepo, setCustomRepo] = useState('');
  const [repoFiles, setRepoFiles] = useState([]);
  const [scanningRepo, setScanningRepo] = useState(false);
  const [selectedFile, setSelectedFile] = useState('');

  useEffect(() => {
    fetch('/api/settings/hf-token')
      .then(r => r.json())
      .then(d => {
        if (d.token) setHfToken('*'.repeat(d.token.length));
      }).catch(() => {});

    fetch('/api/config/settings')
      .then(r => r.json())
      .then(d => {
        setDiscordWebhook(d.discord_webhook || '');
        setTelegramToken(d.telegram_bot_token || '');
        setTelegramChatId(d.telegram_chat_id || '');
        setModelCacheDir(d.model_cache_dir || '');
        setProviders(d.subliminal_providers || []);
    }).catch(() => {});

    fetchLLMModels();
    fetchAllModels();
    fetchNetworkMounts();
  }, []);

  const fetchNetworkMounts = async () => {
    try {
      const resp = await fetch('/api/settings/network-mount');
      const data = await resp.json();
      setNetworkMounts(data || {});
    } catch (err) {
      console.error("Failed to fetch network mounts:", err);
    }
  };

  const fetchAllModels = async () => {
    setLoadingModels(true);
    try {
      const resp = await fetch('/api/models');
      const data = await resp.json();
      setAllModels(data || []);
    } catch (err) {
      console.error("Failed to fetch all models:", err);
    } finally {
      setLoadingModels(false);
    }
  };

  const fetchLLMModels = async () => {
    try {
      const resp = await fetch('/api/llm/models');
      const data = await resp.json();
      setLocalModels(data.local || []);
      setRecommendedModels(data.recommended || []);
      
      // Update downloading set based on progress
      const downloading = new Set();
      data.recommended?.forEach(m => {
        if (m.progress > 0 && m.progress < 100) downloading.add(m.id);
      });
      setDownloadingIds(downloading);
    } catch (err) {
      console.error("Failed to fetch LLM models:", err);
    }
  };

  // Poll for download progress if any are active
  useEffect(() => {
    if (downloadingIds.size === 0) return;
    const interval = setInterval(fetchLLMModels, 2000);
    return () => clearInterval(interval);
  }, [downloadingIds]);

  const handleDownloadModel = async (modelId) => {
    try {
      const resp = await fetch('/api/llm/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId })
      });
      if (resp.ok) {
        setDownloadingIds(prev => new Set([...prev, modelId]));
        fetchLLMModels();
      }
    } catch (err) {
      console.error("Failed to start download:", err);
    }
  };

  const handleScanRepo = async () => {
    setScanningRepo(true);
    setRepoFiles([]);
    setSelectedFile('');
    try {
      const resp = await fetch(`/api/llm/scan?repo_id=${encodeURIComponent(customRepo)}`);
      const data = await resp.json();
      if (resp.ok) {
        setRepoFiles(data.files || []);
        if (data.files?.length === 0) {
          alert("No .gguf files found in this repository.");
        }
      } else {
        alert(data.detail || "Failed to scan repository.");
      }
    } catch (err) {
      console.error("Scan error:", err);
      alert("Failed to reach server for scanning.");
    } finally {
      setScanningRepo(false);
    }
  };

  const handleRegisterAndDownload = async () => {
    try {
      // 1. Register with backend
      const regResp = await fetch('/api/llm/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          repo: customRepo, 
          file: selectedFile,
          name: `Custom: ${selectedFile.split('/').pop()}`
        })
      });
      const regData = await regResp.json();
      if (!regResp.ok) throw new Error(regData.detail || "Registration failed");

      // 2. Trigger download
      await handleDownloadModel(regData.model_id);
      
      // 3. Reset scanner
      setRepoFiles([]);
      setCustomRepo('');
      setSelectedFile('');
    } catch (err) {
      console.error("Register/Download error:", err);
      alert(err.message);
    }
  };

  const handleDeleteModel = async (path) => {
    if (!window.confirm(`Are you sure you want to delete this model?\n${path.split(/[\\/]/).pop()}`)) return;
    try {
      const resp = await fetch(`/api/models?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
      if (resp.ok) {
        fetchAllModels();
        fetchLLMModels();
      }
    } catch (err) {
      console.error("Failed to delete model:", err);
    }
  };

  const handleWipeModels = async () => {
    if (wipeConfirmText !== 'DELETE') return;
    setWiping(true);
    try {
      const resp = await fetch('/api/models/wipe', { method: 'POST' });
      if (resp.ok) {
        setShowWipeConfirm(false);
        setWipeConfirmText('');
        fetchAllModels();
        fetchLLMModels();
        alert("Model cache wiped successfully.");
      }
    } catch (err) {
      alert("Failed to wipe models.");
    } finally {
      setWiping(false);
    }
  };

  const moveProvider = (index, direction) => {
    const newProviders = [...providers];
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= newProviders.length) return;
    const [moved] = newProviders.splice(index, 1);
    newProviders.splice(targetIndex, 0, moved);
    setProviders(newProviders);
  };

  const moveProviderToExtreme = (index, toTop) => {
    const newProviders = [...providers];
    const [moved] = newProviders.splice(index, 1);
    if (toTop) {
      newProviders.unshift(moved);
    } else {
      newProviders.push(moved);
    }
    setProviders(newProviders);
  };

  const toggleProvider = (index) => {
    const newProviders = [...providers];
    const isActive = !newProviders[index].active;
    newProviders[index].active = isActive;
    
    // If we just deactivated it, move it to the bottom
    if (!isActive) {
      const [moved] = newProviders.splice(index, 1);
      newProviders.push(moved);
    }
    setProviders(newProviders);
  };

  const updateProviderCreds = (index, field, value) => {
    const newProviders = [...providers];
    newProviders[index][field] = value;
    setProviders(newProviders);
  };

  const handleSaveToken = async () => {
    setSavingToken(true);
    setTokenStatus('');
    try {
      const resp = await fetch('/api/settings/hf-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: hfToken })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Failed to save token");
      setSavedMessage(data.message);
      setTimeout(() => setSavedMessage(''), 3000);
    } catch (err) {
      setTokenStatus(`Error: ${err.message}`);
    } finally {
      setSavingToken(false);
    }
  };

  const handleMountNetwork = async () => {
    setMounting(true);
    setMountStatus('');
    try {
      const resp = await fetch('/api/settings/network-mount', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(netConfig)
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Failed to mount network");
      setSavedMessage(data.message);
      setTimeout(() => setSavedMessage(''), 3000);
      
      const existing = JSON.parse(localStorage.getItem('as_network_shares') || '[]');
      if (!existing.includes(netConfig.share_path)) {
        localStorage.setItem('as_network_shares', JSON.stringify([...existing, netConfig.share_path]));
      }
      fetchNetworkMounts();
    } catch (err) {
      setMountStatus(`Error: ${err.message}`);
    } finally {
      setMounting(false);
    }
  };

  const handleUnmountNetwork = async (path) => {
    if (!window.confirm(`Are you sure you want to disconnect from ${path}?`)) return;
    try {
      const resp = await fetch(`/api/settings/network-mount?share_path=${encodeURIComponent(path)}`, {
        method: 'DELETE'
      });
      if (resp.ok) {
        fetchNetworkMounts();
      }
    } catch (err) {
      console.error("Failed to unmount:", err);
    }
  };

  const handleSaveNotifications = async () => {
    setSavingNotifs(true);
    setNotifStatus('');
    try {
      const resp = await fetch('/api/config/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          discord_webhook: discordWebhook,
          telegram_bot_token: telegramToken,
          telegram_chat_id: telegramChatId,
          model_cache_dir: modelCacheDir,
          subliminal_providers: providers
        })
      });
      if (!resp.ok) throw new Error("Failed to save notification settings");
      setSavedMessage('Settings saved successfully!');
      setTimeout(() => setSavedMessage(''), 3000);
    } catch (err) {
      setNotifStatus(`Error: ${err.message}`);
    } finally {
      setSavingNotifs(false);
    }
  };

  return (
    <div className="glass-panel" style={{ flex: 1, padding: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem' }}>
        <SettingsIcon size={28} color="var(--primary)" />
        <h2 style={{ margin: 0 }}>Application Settings</h2>
      </div>

      {savedMessage && (
        <div style={{
          position: 'absolute', top: '2rem', right: '2rem',
          background: 'var(--success)', color: 'white', padding: '0.75rem 1.5rem',
          borderRadius: '12px', fontWeight: 'bold', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', zIndex: 9999,
          animation: 'fadeIn 0.2s ease-out', display: 'flex', alignItems: 'center', gap: '0.5rem',
          border: '1px solid rgba(255,255,255,0.1)'
        }}>
          <Check size={18} /> {savedMessage}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        
        {/* HF Token Section */}
        <section style={{ background: 'rgba(0,0,0,0.1)', padding: '1.5rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Shield size={20} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>HuggingFace Authentication</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Provide a HuggingFace Read token to bypass unauthenticated IP rate-limits and drastically speed up model downloads.
          </p>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <input 
              type="password"
              placeholder="hf_..."
              value={hfToken}
              onChange={(e) => setHfToken(e.target.value)}
              className="text-input"
              style={{ flex: 1 }}
            />
            <button 
              className="btn-primary" 
              onClick={handleSaveToken} 
              disabled={savingToken}
            >
              {savingToken ? 'Authenticating...' : 'Save & Auth'}
            </button>
          </div>
          {tokenStatus && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: tokenStatus.startsWith('Error') ? 'var(--danger)' : 'var(--success)' }}>
              {tokenStatus}
            </div>
          )}
        </section>

        {/* Network Mount Section */}
        <section style={{ 
          background: 'rgba(99, 102, 241, 0.05)', 
          padding: '1.5rem', 
          borderRadius: '12px',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Server size={24} color="rgb(129, 140, 248)" />
            <h3 style={{ margin: 0, fontSize: '1.2rem' }}>Manage Network Paths (SMB/NFS)</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Explicitly map and authenticate to network shares natively avoiding `Permission denied` errors. Windows will authenticate your active session to the host natively. Linux will attempt to mount to `/mnt/`.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="form-group">
              <label>Network Path (e.g. \\192.168.1.100\movies)</label>
              <input 
                type="text" 
                className="text-input"
                placeholder="\\server\share OR Z:\" 
                value={netConfig.share_path}
                onChange={(e) => setNetConfig({...netConfig, share_path: e.target.value})}
              />
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Username (Optional)</label>
                <input 
                  type="text" 
                  className="text-input"
                  value={netConfig.username}
                  onChange={(e) => setNetConfig({...netConfig, username: e.target.value})}
                />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Password (Optional)</label>
                <input 
                  type="password" 
                  className="text-input"
                  value={netConfig.password}
                  onChange={(e) => setNetConfig({...netConfig, password: e.target.value})}
                />
              </div>
            </div>
            
            <button 
              className="btn-primary" 
              onClick={handleMountNetwork} 
              disabled={mounting || !netConfig.share_path}
              style={{ alignSelf: 'flex-start' }}
            >
              {mounting ? 'Mapping drive...' : 'Authenticate & Mount'}
            </button>
          </div>
          
          {Object.keys(networkMounts).length > 0 && (
            <div style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
              <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Currently Mapped Shares</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Object.entries(networkMounts).map(([path, creds]) => (
                  <div key={path} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(255,255,255,0.03)', padding: '0.5rem 0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', overflow: 'hidden' }}>
                      <Database size={14} className="text-purple-400" />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-bright)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{path}</span>
                      {creds.username && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', padding: '1px 6px', borderRadius: '4px' }}>as {creds.username}</span>
                      )}
                    </div>
                    <button 
                      onClick={() => handleUnmountNetwork(path)}
                      style={{ padding: '0.25rem', color: 'rgba(239, 68, 68, 0.6)', cursor: 'pointer', background: 'transparent', border: 'none', transition: 'color 0.2s' }}
                      onMouseOver={(e) => e.target.style.color = 'rgb(239, 68, 68)'}
                      onMouseOut={(e) => e.target.style.color = 'rgba(239, 68, 68, 0.6)'}
                      title="Disconnect share"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

           {mountStatus && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: mountStatus.startsWith('Error') ? 'var(--danger)' : 'var(--success)' }}>
              {mountStatus}
            </div>
          )}
        </section>

        {/* Notifications Section */}
        <section style={{ background: 'rgba(0,0,0,0.1)', padding: '1.5rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Bell size={20} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Alert &amp; Notification Integration</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Receive push notifications when jobs complete or fail. Windows natively triggers Desktop Notifications automatically. Configure these for remote server deployments.
          </p>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-muted)' }}>Discord Webhook URL</label>
            <input 
              type="text" 
              placeholder="https://discord.com/api/webhooks/..."
              value={discordWebhook}
              onChange={e => setDiscordWebhook(e.target.value)}
              className="text-input"
              style={{ width: '100%' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-muted)' }}>Telegram Bot Token</label>
              <input 
                type="text" 
                placeholder="123456:ABC-DEF1234gh..."
                value={telegramToken}
                onChange={e => setTelegramToken(e.target.value)}
                className="text-input"
                style={{ width: '100%' }}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-muted)' }}>Telegram Chat ID</label>
              <input 
                type="text" 
                placeholder="-1001234567890"
                value={telegramChatId}
                onChange={e => setTelegramChatId(e.target.value)}
                className="text-input"
                style={{ width: '100%' }}
              />
            </div>
          </div>
          <button 
            className="btn-primary" 
            onClick={handleSaveNotifications}
            disabled={savingNotifs}
            style={{ alignSelf: 'flex-start' }}
          >
            {savingNotifs ? 'Saving...' : 'Save Notification Settings'}
          </button>
          {notifStatus && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: notifStatus.startsWith('Error') ? 'var(--danger)' : 'var(--success)' }}>
              {notifStatus}
            </div>
          )}
        </section>

        {/* Model Storage Section */}
        <section style={{ background: 'rgba(0,0,0,0.1)', padding: '1.5rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Server size={20} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Storage &amp; Models</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Redirect large AI model downloads (Whisper, WhisperX, HuggingFace) to a specific directory. 
            Leave empty to use the default <code>backend/models/</code> folder.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="form-group">
              <label>Model Cache Directory</label>
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
                  className="btn-ghost" 
                  onClick={() => setIsPickerOpen(true)}
                  title="Browse Folder"
                >
                  <Search size={18} /> Browse
                </button>
              </div>
            </div>
            
            <button 
              className="btn-primary" 
              onClick={handleSaveNotifications} // Re-using the same save endpoint for config
              disabled={savingNotifs}
              style={{ alignSelf: 'flex-start' }}
            >
              {savingNotifs ? 'Saving...' : 'Save Storage Settings'}
            </button>
          </div>
        </section>
        {/* Native LLM Section */}
        <section style={{ background: 'rgba(59, 130, 246, 0.05)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Cpu size={20} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Native LLM (llama-cpp-python)</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
            AutoSubs AI uses an <strong>in-process</strong> Native LLM for state-of-the-art translations. 
            No external installation required. Models are stored in your configured cache directory.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Recommended Models */}
            <div>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '1rem', color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Download size={16} /> Recommended &amp; Custom Models
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {recommendedModels.map(model => (
                  <div key={model.id} style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderLeft: model.is_custom ? '3px solid var(--primary)' : 'none' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>
                        {model.name} 
                        <span style={{ fontWeight: 400, fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '8px' }}>({model.size})</span>
                        {model.is_custom && <span style={{ marginLeft: '8px', fontSize: '0.7rem', background: 'rgba(59,130,246,0.2)', color: 'var(--primary)', padding: '2px 6px', borderRadius: '4px' }}>CUSTOM</span>}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{model.description}</div>
                      {model.progress > 0 && model.progress < 100 && (
                        <div style={{ marginTop: '0.5rem', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${model.progress}%`, background: 'var(--primary)', transition: 'width 0.3s ease' }} />
                        </div>
                      )}
                    </div>
                    <button 
                      className={model.is_downloaded ? "btn-ghost-success-sm" : "btn-primary-sm"}
                      onClick={() => !model.is_downloaded && handleDownloadModel(model.id)}
                      disabled={model.is_downloaded || downloadingIds.has(model.id)}
                      style={{ marginLeft: '1rem' }}
                    >
                      {model.is_downloaded ? <><Check size={14} style={{ marginRight: '4px' }} /> Downloaded</> : 
                       downloadingIds.has(model.id) ? 'Downloading...' : 'Download'}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Custom Model Registration */}
            <div style={{ background: 'rgba(0,0,0,0.15)', padding: '1.25rem', borderRadius: '10px', border: '1px dashed rgba(255,255,255,0.1)' }}>
              <h4 style={{ fontSize: '0.85rem', marginBottom: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Globe size={14} /> Download Custom GGUF from HuggingFace
              </h4>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                <input 
                  type="text"
                  className="text-input-sm"
                  placeholder="e.g. bartowski/Qwen_Qwen3.5-9B-GGUF"
                  value={customRepo}
                  onChange={(e) => setCustomRepo(e.target.value)}
                  style={{ flex: 1 }}
                />
                <button 
                  className="btn-ghost-sm" 
                  onClick={handleScanRepo}
                  disabled={scanningRepo || !customRepo}
                >
                  {scanningRepo ? 'Scanning...' : 'Scan Repo'}
                </button>
              </div>

              {repoFiles.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', animation: 'fadeIn 0.3s ease' }}>
                  <select 
                    className="text-input-sm"
                    value={selectedFile}
                    onChange={(e) => setSelectedFile(e.target.value)}
                    style={{ flex: 1, background: 'var(--bg-dark)' }}
                  >
                    <option value="">-- Select .gguf file --</option>
                    {repoFiles.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                  <button 
                    className="btn-primary-sm"
                    onClick={handleRegisterAndDownload}
                    disabled={!selectedFile}
                  >
                    Add &amp; Download
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Model Cache Management (Moved here for better UX) */}
        <section className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Database className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white m-0">Model Cache Management</h2>
                <p className="text-sm text-slate-400">View and manage downloaded AI weights (Whisper, NLLB, GGUF)</p>
              </div>
            </div>
            <button 
              onClick={() => setShowWipeConfirm(true)}
              className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg transition-all text-sm font-medium flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              Wipe Cache
            </button>
          </div>

          {loadingModels ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 text-purple-500 animate-spin" />
            </div>
          ) : allModels.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {allModels.map((model) => (
                <div key={model.path} className="group relative bg-slate-900/40 border border-slate-700/50 rounded-lg p-4 hover:border-purple-500/50 transition-all">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-slate-400" />
                        <span className="text-sm font-medium text-slate-200 capitalize">{model.type}</span>
                    </div>
                    <button 
                      onClick={() => handleDeleteModel(model.path)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-400 transition-all"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <h3 className="text-sm font-semibold text-white mb-1 truncate" title={model.name}>
                    {model.name}
                  </h3>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">{model.size}</span>
                    <span className="text-slate-600 bg-slate-800/50 px-2 py-0.5 rounded italic">
                      {model.path.split(/[\\/]/).pop()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-slate-900/20 rounded-lg border border-dashed border-slate-700/50">
              <Database className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-400">No downloaded models found in the current cache directory.</p>
            </div>
          )}
        </section>

        {/* Subtitle Discovery Section */}
        <section style={{ background: 'rgba(0,0,0,0.1)', padding: '1.5rem', borderRadius: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Globe size={20} color="var(--primary)" />
            <h3 style={{ margin: 0 }}>Subtitle Discovery Providers</h3>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
            Configure and prioritize online subtitle sources. Subliminal will query these in the order listed below.
            Account credentials are required for some providers (e.g. OpenSubtitles VIP).
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
            {providers.map((p, idx) => (
              <div 
                key={p.id} 
                className="glass-panel" 
                style={{ 
                  padding: '1rem', 
                  display: 'flex', 
                  flexDirection: 'column',
                  gap: '1rem',
                  opacity: p.active ? 1 : 0.6,
                  transition: 'opacity 0.2s',
                  background: 'rgba(255,255,255,0.03)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                    <button className="btn-ghost-sm" style={{ padding: '0px 4px', height: '18px' }} onClick={() => moveProviderToExtreme(idx, true)} title="Move to Top" disabled={idx === 0}><ChevronsUp size={12}/></button>
                    <button className="btn-ghost-sm" style={{ padding: '0px 4px', height: '18px' }} onClick={() => moveProvider(idx, -1)} title="Move Up" disabled={idx === 0}><ArrowUp size={12}/></button>
                    <button className="btn-ghost-sm" style={{ padding: '0px 4px', height: '18px' }} onClick={() => moveProvider(idx, 1)} title="Move Down" disabled={idx === (providers.length - 1)}><ArrowDown size={12}/></button>
                    <button className="btn-ghost-sm" style={{ padding: '0px 4px', height: '18px' }} onClick={() => moveProviderToExtreme(idx, false)} title="Move to Bottom" disabled={idx === (providers.length - 1)}><ChevronsDown size={12}/></button>
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{p.id}</span>
                      {p.active ? 
                        <span style={{ fontSize: '0.7rem', background: 'rgba(0,255,0,0.1)', color: '#4ade80', padding: '1px 6px', borderRadius: '10px' }}>ACTIVE</span> :
                        <span style={{ fontSize: '0.7rem', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', padding: '1px 6px', borderRadius: '10px' }}>DISABLED</span>
                      }
                    </div>
                  </div>

                  <button 
                    className={p.active ? "btn-ghost-danger-sm" : "btn-ghost-success-sm"}
                    onClick={() => toggleProvider(idx)}
                    title={p.active ? "Disable" : "Enable"}
                  >
                    {p.active ? <X size={18}/> : <Check size={18}/>}
                  </button>
                </div>

                {p.active && (p.id.includes('opensubtitles') || p.id === 'addic7ed' || p.id === 'subsource' || p.id === 'subdl') && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                    {(p.id !== 'subsource' && p.id !== 'subdl') && (
                      <>
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Username</label>
                          <input 
                            type="text" 
                            placeholder="Username" 
                            className="text-input-sm" 
                            value={p.user || ''} 
                            onChange={e => updateProviderCreds(idx, 'user', e.target.value)}
                            style={{ width: '100%', fontSize: '0.85rem' }}
                          />
                        </div>
                        <div style={{ flex: 1, minWidth: '200px' }}>
                          <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Password</label>
                          <input 
                            type="password" 
                            placeholder="Password" 
                            className="text-input-sm" 
                            value={p.pass || ''} 
                            onChange={e => updateProviderCreds(idx, 'pass', e.target.value)}
                            style={{ width: '100%', fontSize: '0.85rem' }}
                          />
                        </div>
                      </>
                    )}
                    {(p.id === 'opensubtitlescom' || p.id === 'subsource' || p.id === 'subdl') && (
                      <div style={{ flex: '1 1 100%', marginTop: '0.5rem' }}>
                        <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>API Key (Consumer Key)</label>
                        <input 
                          type="password" 
                          placeholder={`Your API Key from ${p.id}.com`} 
                          className="text-input-sm" 
                          value={p.api_key || ''} 
                          onChange={e => updateProviderCreds(idx, 'api_key', e.target.value)}
                          style={{ width: '100%', fontSize: '0.85rem' }}
                        />
                        <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.75rem', color: 'rgba(59, 130, 246, 0.8)' }}>
                          <Info size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                          {p.id === 'subdl' ? 
                            <>Required. Generate your API Key at <strong>subdl.com</strong> (Account → API Key).</> :
                            p.id === 'subsource' ?
                            <>Required. Generate your API Key at <strong>subsource.net</strong> (Profile → My Profile).</> :
                            <>Required for the new .com API. Register at <strong>opensubtitles.com</strong> to get your Consumer Key.</>
                          }
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <button 
            className="btn-primary" 
            onClick={handleSaveNotifications}
            disabled={savingNotifs}
          >
            {savingNotifs ? 'Saving...' : 'Save Provider Priority & Settings'}
          </button>
        </section>

        <div className="h-20" /> {/* Spacer */}
      </div>

      <Modal 
        isOpen={isPickerOpen} 
        onClose={() => setIsPickerOpen(false)} 
        title="Select Model Storage Directory"
      >
        <FolderBrowser 
          onSelect={setModelCacheDir} 
          selectedPath={modelCacheDir} 
        />
      </Modal>

      {/* Wipe Confirmation Modal */}
      {showWipeConfirm && (
        <Modal 
          isOpen={true}
          title="Clear All Models?" 
          onClose={() => {
            setShowWipeConfirm(false);
            setWipeConfirmText('');
          }}
        >
          <div className="p-1">
            <div className="flex items-start gap-4 p-4 bg-red-500/10 rounded-lg border border-red-500/20 mb-6">
              <Shield className="w-6 h-6 text-red-500 shrink-0 mt-1" />
              <div>
                <h3 className="text-red-400 font-semibold mb-1 m-0">Danger Zone</h3>
                <p className="text-sm text-red-300/80 leading-relaxed m-0">
                  This will delete <strong>ALL</strong> downloaded AI models, weights, and caches. You will need to re-download them before you can transcribe or translate again.
                </p>
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Please type <span className="text-white font-bold select-all bg-slate-700 px-1 rounded">DELETE</span> to confirm
              </label>
              <input
                type="text"
                value={wipeConfirmText}
                onChange={(e) => setWipeConfirmText(e.target.value)}
                autoFocus
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-red-500/50 outline-none transition-all placeholder:text-slate-600"
                placeholder="Type 'DELETE' here..."
              />
            </div>

            <div className="flex items-center gap-3 justify-end">
              <button
                onClick={() => {
                  setShowWipeConfirm(false);
                  setWipeConfirmText('');
                }}
                className="px-4 py-2 text-slate-400 hover:text-white transition-colors text-sm font-medium"
              >
                Cancel
              </button>
              <button
                disabled={wipeConfirmText !== 'DELETE' || wiping}
                onClick={handleWipeModels}
                className={`px-6 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 ${
                  wipeConfirmText === 'DELETE' && !wiping
                    ? 'bg-red-500 hover:bg-red-600 text-white shadow-lg shadow-red-500/20'
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }`}
              >
                {wiping ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Wiping everything...
                  </>
                ) : (
                  <>
                    <X className="w-4 h-4" />
                    Wipe All Models
                  </>
                )}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
