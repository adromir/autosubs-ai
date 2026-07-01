import React, { useState, useEffect, useRef } from 'react';
import { Settings, Play, ArrowUp, ArrowDown, X, Save, Plus, Trash2, Edit3, Check, Globe, ChevronRight, ChevronDown, HelpCircle, Info, Film, Languages, Star } from 'lucide-react';
import CustomSelect from './CustomSelect';

const Tooltip = ({ text, children }) => {
  const [show, setShow] = useState(false);
  return (
    <div 
      style={{ position: 'relative', display: 'inline-block', width: '100%' }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div style={{
          position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(15, 23, 42, 0.95)', color: 'white', padding: '0.6rem 0.9rem', 
          borderRadius: '8px', fontSize: '0.85rem', zIndex: 1000, width: '240px', 
          marginBottom: '10px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          backdropFilter: 'blur(8px)', lineHeight: '1.4', pointerEvents: 'none'
        }}>
          {text}
          <div style={{
            position: 'absolute', top: '100%', left: '50%', transform: 'translateX(-50%)',
            borderWidth: '6px', borderStyle: 'solid', borderColor: 'rgba(15, 23, 42, 0.95) transparent transparent transparent'
          }} />
        </div>
      )}
    </div>
  );
};

const CollapsibleSection = ({ title, icon: Icon, isOpen, onToggle, children, helpText }) => {
  const [showInfo, setShowInfo] = useState(false);

  return (
    <div style={{ marginBottom: '1rem', border: '1px solid var(--panel-border)', borderRadius: '12px', overflow: 'hidden' }}>
      <div 
        style={{
          width: '100%', padding: '0.75rem 1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: isOpen ? 'rgba(59, 130, 246, 0.08)' : 'rgba(255,255,255,0.03)', border: 'none', color: 'var(--text)',
          transition: 'background 0.2s'
        }}
      >
        <div onClick={onToggle} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer', flex: 1 }}>
          <Icon size={18} color={isOpen ? 'var(--primary)' : 'var(--text-muted)'} />
          <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{title}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {helpText && (
            <button 
              onClick={() => setShowInfo(!showInfo)}
              type="button" 
              className="btn-ghost" 
              style={{ padding: '0.4rem', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              title="Section Info"
            >
              <HelpCircle size={18} color={showInfo ? 'var(--primary)' : 'var(--text-muted)'} />
            </button>
          )}
          <button 
            onClick={onToggle}
            type="button"
            className="btn-ghost"
            style={{ padding: '0.4rem' }}
          >
            {isOpen ? <ChevronDown size={18} color="var(--text-muted)" /> : <ChevronRight size={18} color="var(--text-muted)" />}
          </button>
        </div>
      </div>
      {isOpen && (
        <div style={{ padding: '1.25rem', borderTop: '1px solid var(--panel-border)' }}>
          {showInfo && helpText && (
            <div style={{ 
              background: 'rgba(59, 130, 246, 0.1)', padding: '1rem', borderRadius: '8px', 
              marginBottom: '1rem', border: '1px solid rgba(59, 130, 246, 0.2)', fontSize: '0.9rem', color: 'var(--text-muted)' 
            }}>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--primary)' }}>
                <Info size={16} />
                <strong style={{ fontSize: '0.85rem', textTransform: 'uppercase' }}>Guidelines</strong>
              </div>
              <div style={{ whiteSpace: 'pre-line' }}>{helpText}</div>
            </div>
          )}
          {children}
        </div>
      )}
    </div>
  );
};

export function ConfigPanel({ onProcess, disabled }) {
  const [hostOs, setHostOs] = useState('unknown');
  const [models, setModels] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [engines, setEngines] = useState([]);
  const [providers, setProviders] = useState([]);

  // New Collapsible State
  const [openSections, setOpenSections] = useState({
    tracks: false,
    engine: false,
    translation: false,
    discovery: false
  });

  const toggleSection = (section) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Profile-related state
  const [profiles, setProfiles] = useState([]);
  const [activeProfileName, setActiveProfileName] = useState('Default');
  const [isNamingNew, setIsNamingNew] = useState(false);
  const [newName, setNewName] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);

  // Transcription parameter state
  const [selectedModel, setSelectedModel] = useState('base');
  const [selectedProvider, setSelectedProvider] = useState('auto');
  const [selectedEngine, setSelectedEngine] = useState('faster-whisper');
  const [selectedBaseLang, setSelectedBaseLang] = useState('en');
  const [selectedLangs, setSelectedLangs] = useState(['en', 'de']);
  const [ignoreForcedSubs, setIgnoreForcedSubs] = useState(true);
  const [useVad, setUseVad] = useState(true);
  const [customPrompt, setCustomPrompt] = useState('');
  const [translationEngine, setTranslationEngine] = useState('nllb');
  const [llmModel, setLlmModel] = useState('');
  const [hardcodeSubs, setHardcodeSubs] = useState(false);
  const [deepCleanup, setDeepCleanup] = useState(true);
  const [vadOnset, setVadOnset] = useState(0.500);
  const [vadOffset, setVadOffset] = useState(0.363);
  const [vadModel, setVadModel] = useState('pyannote');
  const [fallbackToTargets, setFallbackToTargets] = useState(false);
  const [fetchInternetSubs, setFetchInternetSubs] = useState(false);
  const [enableExtraction, setEnableExtraction] = useState(true);
  const [enableTranscription, setEnableTranscription] = useState(true);
  const [embyNaming, setEmbyNaming] = useState(false);
  const [allowTitleMatch, setAllowTitleMatch] = useState(false);
  const [useNfo, setUseNfo] = useState(false);
  const [autoSync, setAutoSync] = useState(false);
  const [autoJanitor, setAutoJanitor] = useState(true);
  const [fetchAllAvailable, setFetchAllAvailable] = useState(false);
  const [isProfileDefault, setIsProfileDefault] = useState(false);
  const [localLlamaModels, setLocalLlamaModels] = useState([]);
  const [llmModelPath, setLlmModelPath] = useState('');

  const [savedMessage, setSavedMessage] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isDropdownOpen]);

  // Dirty State Detection
  const isDirty = (() => {
    const p = profiles.find(pr => pr.name === activeProfileName);
    if (!p) return false;
    
    // Compare each relevant field
    const diffs = [
      selectedModel !== p.model,
      selectedProvider !== p.provider,
      selectedEngine !== p.engine,
      selectedBaseLang !== p.base_lang,
      JSON.stringify(selectedLangs) !== JSON.stringify(p.target_langs || []),
      ignoreForcedSubs !== (p.ignore_forced ?? true),
      useVad !== (p.use_vad ?? true),
      customPrompt !== (p.prompt ?? ''),
      translationEngine !== (p.trans_engine ?? 'nllb'),
      llmModel !== (p.llm_model ?? ''),
      hardcodeSubs !== (p.hardcode ?? false),
      deepCleanup !== (p.deep_cleanup ?? true),
      Math.abs(vadOnset - (p.vad_onset ?? 0.500)) > 0.001,
      Math.abs(vadOffset - (p.vad_offset ?? 0.363)) > 0.001,
      vadModel !== (p.vad_model ?? 'pyannote'),
      fetchInternetSubs !== (p.fetch_internet_subs ?? false),
      enableExtraction !== (p.enable_extraction ?? true),
      enableTranscription !== (p.enable_transcription ?? true),
      embyNaming !== (p.emby_naming ?? false),
      allowTitleMatch !== (p.allow_title_match ?? false),
      useNfo !== (p.use_nfo ?? false),
      autoSync !== (p.auto_sync ?? false),
      autoJanitor !== (p.auto_janitor ?? true),
      fallbackToTargets !== (p.fallback_to_targets ?? false),
      fetchAllAvailable !== (p.fetch_all_available ?? false),
      llmModelPath !== (p.llm_model_path || '')
    ];
    return diffs.some(d => d);
  })();

  const fetchProfiles = async (selectName = null) => {
    try {
      const res = await fetch('/api/profiles/', { cache: 'no-store' });
      const data = await res.json();
      setProfiles(data.profiles || []);
      
      const target = selectName || data.default;
      if (target) {
        const found = data.profiles.find(p => p.name === target);
        if (found) applyProfile(found);
      }
    } catch (e) {
      console.error("Failed to fetch profiles", e);
    }
  };

  const applyProfile = (p) => {
    setActiveProfileName(p.name);
    setSelectedModel(p.model);
    setSelectedProvider(p.provider);
    setSelectedEngine(p.engine);
    setSelectedBaseLang(p.base_lang);
    setSelectedLangs(p.target_langs || []);
    setIgnoreForcedSubs(p.ignore_forced);
    setUseVad(p.use_vad);
    setCustomPrompt(p.prompt);
    setTranslationEngine(p.trans_engine);
    setLlmModel(p.llm_model);
    setHardcodeSubs(p.hardcode);
    setDeepCleanup(p.deep_cleanup !== undefined ? p.deep_cleanup : true);
    setVadOnset(p.vad_onset !== undefined ? p.vad_onset : 0.500);
    setVadOffset(p.vad_offset !== undefined ? p.vad_offset : 0.363);
    setVadModel(p.vad_model);
    setFallbackToTargets(p.fallback_to_targets || false);
    setFetchInternetSubs(p.fetch_internet_subs);
    setEnableExtraction(p.enable_extraction ?? true);
    setEnableTranscription(p.enable_transcription ?? true);
    setEmbyNaming(p.emby_naming ?? false);
    setAllowTitleMatch(p.allow_title_match);
    setUseNfo(p.use_nfo || false);
    setAutoSync(p.auto_sync || false);
    setAutoJanitor(p.auto_janitor ?? true);
    setFetchAllAvailable(p.fetch_all_available || false);
    setIsProfileDefault(p.is_default || false);
    
    // Explicitly handle model path to ensure it's a string
    const loadedPath = p.llm_model_path || '';
    setLlmModelPath(loadedPath);
    console.log(`[Profile] Applied model path for '${p.name}':`, loadedPath);
  };

  const handleSaveProfile = async (targetName = activeProfileName, asDefault = isProfileDefault) => {
    const profile = {
      name: targetName,
      model: selectedModel,
      provider: selectedProvider,
      engine: selectedEngine,
      base_lang: selectedBaseLang,
      target_langs: selectedLangs,
      ignore_forced: ignoreForcedSubs,
      use_vad: useVad,
      prompt: customPrompt,
      trans_engine: translationEngine,
      llm_model: llmModel,
      hardcode: hardcodeSubs,
      deep_cleanup: deepCleanup,
      vad_onset: vadOnset,
      vad_offset: vadOffset,
      vad_model: vadModel,
      fallback_to_targets: fallbackToTargets,
      fetch_internet_subs: fetchInternetSubs,
      enable_extraction: enableExtraction,
      enable_transcription: enableTranscription,
      emby_naming: embyNaming,
      allow_title_match: allowTitleMatch,
      use_nfo: useNfo,
      auto_sync: autoSync,
      fetch_all_available: fetchAllAvailable,
      is_default: isProfileDefault,
      llm_model_path: llmModelPath
    };

    try {
      const resp = await fetch('/api/profiles/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile)
      });
      if (resp.ok) {
        setSavedMessage(`Profile '${targetName}' Saved!`);
        setIsNamingNew(false);
        fetchProfiles(targetName);
        setTimeout(() => setSavedMessage(''), 2500);
      }
    } catch (e) {
      console.error("Failed to save profile", e);
    }
  };

  const handleDeleteProfile = async () => {
    if (!window.confirm(`Delete profile '${activeProfileName}'?`)) return;
    try {
      await fetch(`/api/profiles/${activeProfileName}`, { method: 'DELETE' });
      fetchProfiles();
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  const handleRename = async () => {
    if (!newName) return;
    try {
      await fetch('/api/profiles/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_name: activeProfileName, new_name: newName })
      });
      setIsRenaming(false);
      fetchProfiles(newName);
    } catch (e) {
      console.error("Rename failed", e);
    }
  };

  const handleSetDefault = async () => {
    try {
      await fetch('/api/profiles/set-default', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: activeProfileName })
      });
      fetchProfiles(activeProfileName);
    } catch (e) {
      console.error("Set default failed", e);
    }
  };

  useEffect(() => {
    async function loadConfig() {
      try {
        const [modRes, lanRes, engRes, hwRes, setRes] = await Promise.all([
          fetch('/api/config/models', { cache: 'no-store' }),
          fetch('/api/config/languages', { cache: 'no-store' }),
          fetch('/api/config/engines', { cache: 'no-store' }),
          fetch('/api/config/hardware', { cache: 'no-store' }),
          fetch('/api/config/settings', { cache: 'no-store' })
        ]);
        
        const modData = await modRes.json();
        const lanData = await lanRes.json();
        const engData = await engRes.json();
        const hwData = await hwRes.json();
        await setRes.json();

        // Fetch local GGUF models for Native LLM
        try {
          const llmRes = await fetch('/api/llm/models');
          const llmData = await llmRes.json();
          setLocalLlamaModels(llmData.local || []);
        } catch (e) {
          console.error("Failed to fetch LLM models", e);
        }
        
        setModels(modData.models || []);
        setLanguages(lanData.languages || []);
        setEngines(engData.engines || []);
        setProviders(hwData.providers || []);
        setHostOs(hwData.os || 'unknown');
        
        fetchProfiles();
      } catch (err) {
        console.error("Failed to load configs", err);
      }
    }
    loadConfig();
  }, []);

  const addLang = (code) => {
    if (!selectedLangs.includes(code)) {
      setSelectedLangs([...selectedLangs, code]);
    }
  };

  const removeLang = (code) => {
    setSelectedLangs(selectedLangs.filter(l => l !== code));
  };
  
  const moveLang = (index, direction) => {
    const newLangs = [...selectedLangs];
    const targetIdx = index + direction;
    if (targetIdx >= 0 && targetIdx < newLangs.length) {
      [newLangs[index], newLangs[targetIdx]] = [newLangs[targetIdx], newLangs[index]];
      setSelectedLangs(newLangs);
    }
  };

  return (
    <div className="glass-panel">
      {/* Premium Profile Management Header */}
      <div style={{ position: 'relative', zIndex: 100, marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Logo/Section Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', padding: '0.5rem 0.2rem' }}>
            <Settings size={22} color="var(--primary)" />
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.01em' }}>Configuration</h3>
          </div>

          {/* New Custom Dropdown Selection */}
          <div ref={dropdownRef} style={{ position: 'relative', flex: 1 }}>
            <button 
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="btn-ghost"
              style={{ 
                width: '100%', justifyContent: 'space-between', padding: '0.75rem 1.25rem', 
                background: 'rgba(255,255,255,0.03)', border: '1px solid var(--panel-border)', 
                borderRadius: '12px', textAlign: 'left', minHeight: '52px', overflow: 'hidden'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ 
                  width: '10px', height: '10px', borderRadius: '50%', 
                  background: isDirty ? 'var(--warning)' : 'var(--success)',
                  boxShadow: isDirty ? '0 0 10px var(--warning)' : 'none'
                }} />
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1, marginBottom: '2px' }}>Active Profile</div>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{activeProfileName} {profiles.find(p => p.name === activeProfileName)?.is_default && "(Default)"}</div>
                </div>
              </div>
              <ChevronDown size={18} color="var(--text-muted)" style={{ transform: isDropdownOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
            </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && (
              <div className="scale-in" style={{ 
                position: 'absolute', top: 'calc(100% + 8px)', right: 0, 
                minWidth: '320px', width: 'max-content', maxWidth: '400px',
                background: 'rgba(15, 23, 42, 0.98)', backdropFilter: 'blur(12px)',
                border: '1px solid var(--panel-border)', borderRadius: '14px', 
                boxShadow: '0 20px 40px rgba(0,0,0,0.6)', padding: '0.5rem', zIndex: 200
              }}>
                <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: '0.5rem' }}>
                  {profiles.map(p => (
                    <button 
                      key={p.name}
                      autoFocus={p.name === activeProfileName}
                      onClick={() => { applyProfile(p); setIsDropdownOpen(false); }}
                      onKeyDown={e => { if(e.key === 'Escape') setIsDropdownOpen(false); }}
                      style={{ 
                        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '0.75rem 1rem', borderRadius: '8px', border: 'none', background: 'transparent',
                        color: p.name === activeProfileName ? 'var(--primary)' : 'white', cursor: 'pointer',
                        transition: 'all 0.15s'
                      }}
                      className="profile-item"
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ width: '4px', height: '16px', borderRadius: '2px', background: p.name === activeProfileName ? 'var(--primary)' : 'transparent' }} />
                        <span style={{ fontWeight: p.name === activeProfileName ? 700 : 500 }}>{p.name}</span>
                        {p.is_default && <span style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-muted)' }}>DEFAULT</span>}
                      </div>
                      {p.name === activeProfileName && <Check size={16} />}
                    </button>
                  ))}
                </div>
                
                {/* Actions Section in Dropdown */}
                <div style={{ borderTop: '1px solid var(--panel-border)', paddingTop: '0.5rem', display: 'flex', gap: '0.25rem' }}>
                  <button 
                    onClick={() => { setNewName(`${activeProfileName} Copy`); setIsNamingNew(true); setIsDropdownOpen(false); }}
                    className="btn-ghost" style={{ flex: 1, fontSize: '0.8rem', padding: '0.5rem' }}
                  >
                    <Plus size={14} /> New From Copy
                  </button>
                  <button 
                    onClick={() => { setNewName(activeProfileName); setIsRenaming(true); setIsDropdownOpen(false); }}
                    className="btn-ghost" style={{ flex: 1, fontSize: '0.8rem', padding: '0.5rem' }}
                  >
                    <Edit3 size={14} /> Rename
                  </button>
                  <button 
                    onClick={() => { handleSetDefault(); setIsDropdownOpen(false); }}
                    className="btn-ghost" style={{ flex: 1, fontSize: '0.8rem', padding: '0.5rem', color: 'var(--warning)' }}
                    disabled={profiles.find(p => p.name === activeProfileName)?.is_default}
                  >
                    <Star size={14} /> Set Default
                  </button>
                  <button 
                    onClick={() => { handleDeleteProfile(); setIsDropdownOpen(false); }}
                    className="btn-ghost" style={{ flex: 1, fontSize: '0.8rem', padding: '0.5rem', color: 'var(--danger)' }}
                    disabled={profiles.length <= 1}
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Quick Actions Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button 
              onClick={() => handleSaveProfile()}
              className={`btn-primary ${isDirty ? 'dirty-pulse' : ''}`}
              style={{ 
                padding: '0.75rem 1.25rem', height: '52px', background: isDirty ? 'var(--warning)' : 'var(--primary)',
                color: isDirty ? 'black' : 'white', fontWeight: 700, borderRadius: '12px',
                minWidth: '100px'
              }}
              title={isDirty ? "Configuration has unsaved changes" : "Everything saved"}
            >
              <Save size={18} /> {isDirty ? 'Save Changes' : 'Save'}
            </button>
          </div>
        </div>

        {/* Floating Forms overlay */}
        {(isNamingNew || isRenaming) && (
          <div className="scale-in" style={{ 
            marginTop: '1rem', background: 'rgba(59, 130, 246, 0.05)', padding: '1.25rem', 
            borderRadius: '12px', border: '1px solid rgba(59, 130, 246, 0.2)',
            display: 'flex', gap: '1rem', alignItems: 'center', animation: 'fadeIn 0.3s ease-out'
          }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '0.7rem', color: 'var(--primary)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                {isNamingNew ? "Create New Profile" : "Rename Current Profile"}
              </label>
              <input 
                autoFocus
                className="text-input"
                placeholder="Enter profile name..."
                value={newName}
                onChange={e => setNewName(e.target.value)}
                onKeyDown={e => { if(e.key === 'Enter') isRenaming ? handleRename() : handleSaveProfile(newName, false); if(e.key === 'Escape') { setIsNamingNew(false); setIsRenaming(false); }}}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignSelf: 'flex-end', marginBottom: '2px' }}>
               <button className="btn-primary" onClick={() => isRenaming ? handleRename() : handleSaveProfile(newName, false)}>
                 {isRenaming ? "Update" : "Create"}
               </button>
               <button className="btn-ghost" onClick={() => { setIsNamingNew(false); setIsRenaming(false); }}>Cancel</button>
            </div>
          </div>
        )}

      </div>

      {/* Logical Control Groups */}
      
      <CollapsibleSection 
        title="Media & Track Selection" 
        icon={Film} 
        isOpen={openSections.tracks} 
        onToggle={() => toggleSection('tracks')}
        helpText={`Base Language: The primary audio language of the video. All translations are derived from this.
Target Languages: Subtitles will be generated for these specific languages.
Exclude Forced: Skips existing subtitle tracks marked as 'Forced'.
Hardcode: Permanently burns the subtitles into the video (requires re-encoding).`}
      >
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>Base Language (Audio Source)</label>
          <CustomSelect 
            value={selectedBaseLang} 
            onChange={(e) => setSelectedBaseLang(e.target.value)}
            options={languages.map(l => ({ value: l.code, label: l.name }))}
          />
        </div>

        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>Target Languages (Translation)</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
            {selectedLangs.map((code, index) => {
              const langName = languages.find(l => l.code === code)?.name || code;
              return (
                <div key={code} style={{ 
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', 
                  background: 'rgba(255,255,255,0.05)', padding: '0.5rem 1rem', 
                  borderRadius: '8px', border: '1px solid var(--panel-border)' 
                }}>
                  <span>{index + 1}. {langName}</span>
                  <div style={{ display: 'flex', gap: '0.25rem' }}>
                    <button onClick={() => moveLang(index, -1)} disabled={index === 0} style={{ padding: '0.2rem', background: 'transparent', cursor: 'pointer', border: 'none', color: 'white' }}><ArrowUp size={16} /></button>
                    <button onClick={() => moveLang(index, 1)} disabled={index === selectedLangs.length - 1} style={{ padding: '0.2rem', background: 'transparent', cursor: 'pointer', border: 'none', color: 'white' }}><ArrowDown size={16} /></button>
                    <button onClick={() => removeLang(code)} style={{ padding: '0.2rem', background: 'transparent', cursor: 'pointer', border: 'none', color: 'var(--danger)' }}><X size={16} /></button>
                  </div>
                </div>
              );
            })}
          </div>

          <CustomSelect 
              value="" 
              onChange={e => addLang(e.target.value)}
              placeholder="+ Add Target Language"
              options={languages.filter(l => !selectedLangs.includes(l.code)).map(l => ({ value: l.code, label: l.name }))}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={ignoreForcedSubs} 
              onChange={e => setIgnoreForcedSubs(e.target.checked)} 
              id="ignoreForced"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="ignoreForced" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
              Exclude "Forced" Subtitles (Partial Movie Languages)
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={enableExtraction} 
              onChange={e => setEnableExtraction(e.target.checked)} 
              id="enableExtraction"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="enableExtraction" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
              Extract Embedded Subtitle Tracks
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={hardcodeSubs} 
              onChange={e => setHardcodeSubs(e.target.checked)} 
              id="hardcodeSubs"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="hardcodeSubs" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
              Hardcode (Burn-in) Subtitles to Output Video
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={embyNaming} 
              onChange={e => setEmbyNaming(e.target.checked)} 
              id="embyNaming"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="embyNaming" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
              Emby Compatible Naming (.eng.srt)
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={autoJanitor} 
              onChange={e => setAutoJanitor(e.target.checked)} 
              id="autoJanitor"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="autoJanitor" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
              Auto Janitor (Clean .tmp.wav files after queue finishes)
            </label>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.25rem', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <input 
              type="checkbox" 
              checked={fallbackToTargets} 
              onChange={e => setFallbackToTargets(e.target.checked)} 
              id="fallbackToTargets"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="fallbackToTargets" style={{ fontWeight: 600, color: 'white', cursor: 'pointer', fontSize: '0.9rem' }}>
              Fallback to Target Languages
              <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400, marginTop: '2px' }}>
                If base language isn't found, repeat search/extraction with all target languages.
              </span>
            </label>
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection 
        title="AI Transcription Engine" 
        icon={Settings} 
        isOpen={openSections.engine} 
        onToggle={() => toggleSection('engine')}
        helpText={`Model Size: Larger models (Medium/Large) provide much better accuracy but require significantly more VRAM and time.
VAD (Voice Activity Detection): Filters out background noise and non-speech audio to prevent transcription hallucinations.`}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>Model Size</label>
            <CustomSelect 
              value={selectedModel} 
              onChange={(e) => setSelectedModel(e.target.value)}
              options={models.map(m => ({ value: m, label: m.charAt(0).toUpperCase() + m.slice(1) }))}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>Engine & Hardware</label>
            <CustomSelect 
              value={selectedEngine} 
              onChange={(e) => setSelectedEngine(e.target.value)}
              options={engines.map(eng => ({ value: eng.id, label: eng.name }))}
            />
          </div>
        </div>

        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>Custom Vocabulary / Prompt</label>
          <textarea
            style={{ 
              width: '100%', padding: '0.75rem', borderRadius: '8px', 
              background: 'rgba(255,255,255,0.05)', border: '1px solid var(--panel-border)', color: 'white', 
              outline: 'none', resize: 'vertical', minHeight: '60px' 
            }}
            placeholder="e.g. Jedi, Coruscant, Skywalker"
            value={customPrompt}
            onChange={e => setCustomPrompt(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={enableTranscription} 
              onChange={e => setEnableTranscription(e.target.checked)} 
              id="enableTranscription"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="enableTranscription" style={{ fontWeight: 600, color: 'var(--text)', cursor: 'pointer' }}>
              Enable AI Transcription
            </label>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', opacity: enableTranscription ? 1 : 0.5, pointerEvents: enableTranscription ? 'auto' : 'none' }}>
            <input 
              type="checkbox" 
              checked={useVad} 
              onChange={e => setUseVad(e.target.checked)} 
              id="useVadSec"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="useVadSec" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
              Enable VAD (Voice Activity Detection) Filter
            </label>
          </div>
        </div>

        {useVad && enableTranscription && (
          <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>VAD Model Preference</label>
              <CustomSelect 
                value={vadModel} 
                onChange={e => setVadModel(e.target.value)}
                options={[
                  { value: 'pyannote', label: 'Pyannote VAD (High Quality, 2.5GB VRAM)' },
                  { value: 'silero', label: 'Silero VAD (Fastest, Light, v5.1)' }
                ]}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <Tooltip text="Sensitivity for Detecting Speech ONSET (Start). Lower values (0.4) catch more beginnings but may hallucinate; Higher values (0.6) are safer.">
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'help' }}>
                    VAD Onset Threshold: {vadOnset.toFixed(2)}
                  </label>
                </Tooltip>
                <input type="range" min="0" max="1" step="0.05" value={vadOnset} onChange={e => setVadOnset(parseFloat(e.target.value))} style={{ width: '100%' }} />
              </div>
              <div>
                <Tooltip text="Sensitivity for Detecting Speech OFFSET (End). Higher values (0.5+) keep the detection active longer, preventing word-clipping at the end of sentences.">
                  <label style={{ display: 'block', marginBottom: '0.4rem', fontSize: '0.85rem', color: 'var(--text-muted)', cursor: 'help' }}>
                    VAD Offset Threshold: {vadOffset.toFixed(2)}
                  </label>
                </Tooltip>
                <input type="range" min="0" max="1" step="0.05" value={vadOffset} onChange={e => setVadOffset(parseFloat(e.target.value))} style={{ width: '100%' }} />
              </div>
            </div>
          </div>
        )}
      </CollapsibleSection>

      <CollapsibleSection 
        title="Translation Parameters" 
        icon={Languages} 
        isOpen={openSections.translation} 
        onToggle={() => toggleSection('translation')}
        helpText={`NLLB-200: A high-fidelity local translation model that runs on your hardware.
Ollama: Integrates with local Large Language Models (LLMs) for context-aware, human-like translations.
Deep Cleanup: Advanced post-processing to fix formatting, remove duplicate lines, and ensure consistent styling across the entire video.`}
      >
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>Translation Engine</label>
            <CustomSelect 
              value={translationEngine} 
              onChange={(e) => setTranslationEngine(e.target.value)}
              options={[
                { value: 'nllb', label: 'NLLB-200 (Default, Fast)' },
                { value: 'native', label: 'Native LLM (In-Process GGUF)' }
              ]}
            />
          </div>
          {translationEngine === 'native' && (
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500, color: 'var(--text-muted)' }}>GGUF Model</label>
              <CustomSelect 
                value={llmModelPath || ''}
                onChange={e => {
                  const val = e.target.value;
                  console.log("[UI] Model selected:", val);
                  setLlmModelPath(val);
                }}
                placeholder="Select a model..."
                options={localLlamaModels.map(m => ({ value: m, label: m }))}
              />
              {localLlamaModels.length === 0 && (
                <p style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem' }}>
                  No models found. Download one in Settings.
                </p>
              )}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <input 
            type="checkbox" 
            checked={deepCleanup} 
            onChange={e => setDeepCleanup(e.target.checked)} 
            id="deepCleanup"
            style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
          />
          <label htmlFor="deepCleanup" style={{ fontWeight: 500, color: 'var(--text)', cursor: 'pointer' }}>
            Enable LLM "Deep Cleanup" (Refine formatting & style)
          </label>
        </div>
      </CollapsibleSection>

      <CollapsibleSection 
        title="Internet Discovery" 
        icon={Globe} 
        isOpen={openSections.discovery} 
        onToggle={() => toggleSection('discovery')}
        helpText={`Internet Discovery searches for community-provided subtitles before attempting AI transcription.
This saves significant time and often results in higher quality 'official' translations.
IMPORTANT: You MUST enable and prioritize your preferred providers (e.g., OpenSubtitles, Subscene) in the 'Settings' tab for this feature to function.`}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ padding: '0.75rem 1rem', background: 'rgba(234, 179, 8, 0.1)', border: '1px solid rgba(234, 179, 8, 0.3)', borderRadius: '8px', marginBottom: '0.5rem' }}>
             <p style={{ margin: 0, fontSize: '0.85rem', color: '#eab308', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.50rem' }}>
               <Settings size={14} /> Provider Setup Required
             </p>
             <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem', color: 'rgba(234, 179, 8, 0.8)' }}>
               Ensure your providers are configured and ranked in the <strong>Settings</strong> tab.
             </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input 
              type="checkbox" 
              checked={fetchInternetSubs} 
              onChange={e => {
                const val = e.target.checked;
                setFetchInternetSubs(val);
                if (!val) {
                  setFetchAllAvailable(false);
                  setAllowTitleMatch(false);
                  setUseNfo(false);
                  setAutoSync(false);
                }
              }} 
              id="fetchInternetSec"
              style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
            <label htmlFor="fetchInternetSec" style={{ fontWeight: 600, color: 'var(--text)', cursor: 'pointer' }}>
              Search Internet for existing Subtitles
            </label>
          </div>

          <div style={{ marginLeft: '1.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', opacity: fetchInternetSubs ? 1 : 0.5, pointerEvents: fetchInternetSubs ? 'auto' : 'none' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <input 
                type="checkbox" 
                checked={fetchAllAvailable} 
                onChange={e => setFetchAllAvailable(e.target.checked)} 
                disabled={!fetchInternetSubs}
                id="fetchAllAvailable"
                style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}
              />
              <label htmlFor="fetchAllAvailable" style={{ fontWeight: 600, color: 'var(--primary)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}>
                Download ALL Available Languages (Bulk Discovery)
              </label>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <input 
                type="checkbox" 
                checked={allowTitleMatch} 
                onChange={e => setAllowTitleMatch(e.target.checked)} 
                disabled={!fetchInternetSubs}
                id="allowTitleMatch"
                style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}
              />
              <label htmlFor="allowTitleMatch" style={{ fontWeight: 500, color: 'var(--text)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}>
                Allow "Fuzzy" Title Matching (less precise)
              </label>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <input 
                type="checkbox" 
                checked={useNfo} 
                onChange={e => setUseNfo(e.target.checked)} 
                disabled={!fetchInternetSubs}
                id="useNfo"
                style={{ width: '18px', height: '18px', accentColor: 'var(--primary)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}
              />
              <label htmlFor="useNfo" style={{ fontWeight: 500, color: 'var(--text)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}>
                Search metadata in local .nfo files (IMDb ID)
              </label>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <input 
                type="checkbox" 
                checked={autoSync} 
                onChange={e => setAutoSync(e.target.checked)} 
                disabled={!fetchInternetSubs}
                id="autoSyncSec"
                style={{ width: '16px', height: '16px', accentColor: 'var(--primary)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}
              />
              <label htmlFor="autoSyncSec" style={{ color: fetchInternetSubs ? 'white' : 'var(--text-muted)', cursor: fetchInternetSubs ? 'pointer' : 'default' }}>
                Auto-Sync non-exact matches via FFsubsync
              </label>
            </div>
          </div>
        </div>
      </CollapsibleSection>

      {/* Action Footer */}
      <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
        <button 
          className="btn-primary"
          style={{ flex: 1, padding: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}
          disabled={disabled || selectedLangs.length === 0}
          onClick={() => onProcess({ 
            model: selectedModel, 
            languages: selectedLangs, 
            baseLanguage: selectedBaseLang, 
            provider: selectedProvider, 
            engine: selectedEngine,
            ignoreForcedSubs: ignoreForcedSubs,
            customPrompt: customPrompt,
            use_vad: useVad,
            translationEngine: translationEngine,
            llm_model_path: llmModelPath,
            hardcodeSubs: hardcodeSubs,
            fetch_internet_subs: fetchInternetSubs,
            enable_extraction: enableExtraction,
            enable_transcription: enableTranscription,
            emby_naming: embyNaming,
            allow_title_match: allowTitleMatch,
            use_nfo: useNfo,
            auto_sync: autoSync,
            vad_onset: vadOnset,
            vad_offset: vadOffset,
            vad_model: vadModel,
            fallback_to_targets: fallbackToTargets,
            fetch_all_available: fetchAllAvailable
          })}
        >
          <Play size={20} />
          <span style={{ fontWeight: 'bold' }}>Start Batch Processing</span>
        </button>
      </div>
      
      {savedMessage && (
        <div style={{
          position: 'absolute', top: '4.5rem', right: '2rem',
          background: 'var(--success)', color: 'white', padding: '0.75rem 1.5rem',
          borderRadius: '12px', fontWeight: 'bold', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', zIndex: 9999,
          animation: 'fadeIn 0.2s ease-out', display: 'flex', alignItems: 'center', gap: '0.5rem',
          border: '1px solid rgba(255,255,255,0.1)'
        }}>
          <Check size={18} /> {savedMessage}
        </div>
      )}
    </div>
  );
}
