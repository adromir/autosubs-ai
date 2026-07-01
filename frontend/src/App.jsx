import React, { useState, useEffect } from 'react';
import { FolderBrowser } from './components/FolderBrowser';
import { ConfigPanel } from './components/ConfigPanel';
import { JobQueue } from './components/JobQueue';
import { Settings } from './components/Settings';
import { ConsoleLog } from './components/ConsoleLog';
import { Login } from './components/Login';
import { Tv, Settings as SettingsIcon, ArrowLeft, Terminal, RefreshCw, LogOut } from 'lucide-react';
import './App.css';

// Intercept global fetch to add Auth header
const originalFetch = window.fetch;
window.fetch = async function () {
  let [resource, config] = arguments;
  
  if (typeof resource === 'string' && resource.startsWith('/api') && !resource.startsWith('/api/auth/login')) {
    const token = localStorage.getItem('api_token');
    if (token) {
      if (!config) config = {};
      if (!config.headers) config.headers = {};
      
      if (config.headers instanceof Headers) {
        config.headers.set('Authorization', `Bearer ${token}`);
      } else if (Array.isArray(config.headers)) {
        // Prevent duplicate if modifying an array
        const authIndex = config.headers.findIndex(h => h[0].toLowerCase() === 'authorization');
        if (authIndex >= 0) config.headers[authIndex][1] = `Bearer ${token}`;
        else config.headers.push(['Authorization', `Bearer ${token}`]);
      } else {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
    }
  }
  
  const response = await originalFetch(resource, config);
  
  // If we hit a 401 on an API route, trigger a logout
  if (response.status === 401 && typeof resource === 'string' && resource.startsWith('/api') && !resource.startsWith('/api/auth/login')) {
    localStorage.removeItem('api_token');
    window.dispatchEvent(new Event('auth-expired'));
    }
  
  return response;
};

function App() {
  const [selectedPath, setSelectedPath] = useState(null);
  const [view, setView] = useState('home'); // home or settings
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('api_token'));

  useEffect(() => {
    const handleAuthExpired = () => setIsAuthenticated(false);
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('api_token');
    setIsAuthenticated(false);
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    
    const token = localStorage.getItem('api_token');
    const eventSource = new EventSource(`/api/jobs/stream?token=${encodeURIComponent(token)}`);
    
    eventSource.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === 'init') {
        setJobs(msg.jobs);
      } else if (msg.type === 'update') {
        setJobs(prev => {
          const idx = prev.findIndex(j => j.id === msg.job.id);
          if (idx === -1) {
            return [...prev, msg.job].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
          }
          const next = [...prev];
          next[idx] = msg.job;
          return next;
        });
      } else if (Array.isArray(msg)) {
        setJobs(msg);
      }
    };

    eventSource.onerror = (error) => {
      console.error("SSE Error", error);
    };

    return () => {
      eventSource.close();
    };
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  const handleRestart = async () => {
    if (!window.confirm("Are you sure you want to restart the backend server? Active transcriptions will be interrupted.")) return;
    setRestarting(true);
    try {
      await fetch('/api/settings/restart', { method: 'POST' });
      setTimeout(() => window.location.reload(), 5000);
    } catch (e) {
      setRestarting(false);
    }
  };

  const handleProcess = async (config) => {
    if (!selectedPath) return;
    setIsSubmitting(true);

    try {
      const resp = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: selectedPath,
          target_languages: config.languages,
          base_language: config.baseLanguage,
          model_size: config.model,
          provider: config.provider,
          engine: config.engine,
          ignore_forced_subs: config.ignoreForcedSubs,
          custom_prompt: config.customPrompt,
          use_vad: config.use_vad,
          translation_engine: config.translationEngine,
          llm_model_path: config.llm_model_path,
          hardcode_subs: config.hardcodeSubs,
          fetch_internet_subs: config.fetch_internet_subs,
          enable_extraction: config.enable_extraction,
          enable_transcription: config.enable_transcription,
          emby_naming: config.emby_naming,
          allow_title_match: config.allow_title_match,
          use_nfo: config.use_nfo,
          auto_sync: config.auto_sync,
          vad_onset: config.vad_onset,
          vad_offset: config.vad_offset,
          vad_model: config.vad_model,
          fetch_all_available: config.fetch_all_available,
          fallback_to_targets: config.fallback_to_targets,
          deep_cleanup: config.deep_cleanup,
          auto_janitor: config.auto_janitor
        })
      });
      if (!resp.ok) {
        const errorData = await resp.json();
        throw new Error(errorData.detail || "Failed to start processing");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const isBusy = jobs.some(j => !['completed', 'failed', 'cancelled'].includes(j.status));

  return (
    <>
      <header className="app-header">
        <div className="brand-group">
          <img src="/logo.png" alt="AutoSubs AI Logo" className="brand-logo" />
          <div>
            <h1 style={{ marginBottom: 0 }}>AutoSubs AI</h1>
            <p style={{ color: 'var(--text-muted)' }}>Automate AI translation & transcription for your media</p>
          </div>
        </div>
        
        <div className="button-groups-container">
          {/* Group 1: App Navigation */}
          <div className="system-group">
            {view === 'home' ? (
              <button 
                onClick={() => setView('settings')} 
                title="Open Settings"
              >
                <SettingsIcon size={20} /> Settings
              </button>
            ) : (
              <button 
                onClick={() => setView('home')} 
                title="Back to Dashboard"
              >
                <Tv size={20} /> Dashboard
              </button>
            )}
            <button
              onClick={handleLogout}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors text-red-400 hover:bg-gray-800`}
            >
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </div>

          {/* Group 2: Server Control (Semantically Grouped) */}
          <div className="system-group">
            <button 
              onClick={() => setIsConsoleOpen(!isConsoleOpen)}
              title="Open Server Control Center"
            >
              <Terminal size={20} /> Console
            </button>
            <button
              onClick={handleRestart}
              disabled={restarting}
              className={restarting ? 'btn-restarting' : undefined}
            >
              <RefreshCw size={20} style={{ animation: restarting ? 'spin 1s linear infinite' : 'none' }} />
              {restarting ? 'Restarting...' : 'Restart'}
            </button>
            <button 
              onClick={async () => {
                if (window.confirm("Are you sure you want to instantly kill the AutoSubs AI Server? This will terminate all active background extractions/models immediately.")) {
                  try {
                    await fetch('/api/shutdown', { method: 'POST' });
                    window.close();
                  } catch (e) {
                    console.error("Shutdown call executed:", e);
                  }
                }
              }}
              className="btn-danger"
            >
              Kill Server
            </button>
          </div>
        </div>
      </header>
      
      <main className="layout-container">
        {view === 'settings' ? (
          <Settings />
        ) : (
          <div className="grid-cols-2">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              <FolderBrowser onSelect={setSelectedPath} selectedPath={selectedPath} />
              <ConfigPanel onProcess={handleProcess} disabled={!selectedPath || isBusy || isSubmitting} />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <JobQueue jobs={jobs} />
            </div>
          </div>
        )}
      </main>
      
      {/* Absolute Mount Web Console Log Overlay */}
      <ConsoleLog isOpen={isConsoleOpen} setIsOpen={setIsConsoleOpen} />
    </>
  )
}

export default App;
