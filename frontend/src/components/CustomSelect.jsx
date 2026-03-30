import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check } from 'lucide-react';

const CustomSelect = ({ options, value, onChange, placeholder, disabled }) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef(null);
  const dropdownRef = useRef(null);
  const [coords, setCoords] = useState({ top: 0, left: 0, width: 0 });

  const selectedOption = options.find(opt => opt.value === value);

  useEffect(() => {
    const updatePosition = () => {
      if (isOpen && triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        setCoords({
          top: rect.bottom + 6, // 6px gap below trigger
          left: rect.left,
          width: rect.width
        });
      }
    };

    if (isOpen) {
      updatePosition();
      // Listen to scroll events in the capture phase to track scrolling in any container
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
    }

    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isOpen]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (triggerRef.current && !triggerRef.current.contains(event.target) &&
          dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const dropdownContent = isOpen && !disabled ? (
    <div 
      ref={dropdownRef}
      className="custom-select-options-wrapper"
      style={{
        position: 'fixed',
        top: `${coords.top}px`,
        left: `${coords.left}px`,
        width: `${coords.width}px`,
        zIndex: 99999
      }}
    >
      {/* Dedicated Glass Layer isolated from overflow clipping */}
      <div 
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.70)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.8)',
          pointerEvents: 'none'
        }}
      />
      {/* Separate Scroll Container */}
      <div 
        className="scrollbar-hidden"
        style={{
          position: 'relative',
          maxHeight: '300px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          padding: '4px'
        }}
      >
        {options.map((opt) => (
          <div
            key={opt.value}
            onClick={() => {
              if (opt.disabled) return;
              onChange({ target: { value: opt.value } });
              setIsOpen(false);
            }}
            style={{
              padding: '0.75rem 1rem',
              cursor: opt.disabled ? 'not-allowed' : 'pointer',
              color: opt.disabled ? 'var(--text-muted)' : (opt.value === value ? 'var(--primary-light, white)' : 'white'),
              background: opt.value === value ? 'rgba(100, 50, 255, 0.15)' : 'transparent',
              borderRadius: '6px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontFamily: "'Inter', 'Noto Color Emoji', sans-serif",
              fontSize: '0.95rem',
              transition: 'background 0.2s, color 0.2s',
              fontWeight: opt.value === value ? 500 : 400,
              marginBottom: '2px'
            }}
            onMouseEnter={(e) => {
              if (!opt.disabled && opt.value !== value) e.target.style.background = 'rgba(255, 255, 255, 0.05)';
            }}
            onMouseLeave={(e) => {
              if (!opt.disabled && opt.value !== value) e.target.style.background = 'transparent';
            }}
          >
            {opt.label}
          </div>
        ))}
      </div>
    </div>
  ) : null;

  return (
    <div style={{ position: 'relative', width: '100%', opacity: disabled ? 0.5 : 1 }}>
      <div 
        ref={triggerRef}
        className="custom-select-trigger"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        style={{
          background: 'rgba(0, 0, 0, 0.40)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: isOpen ? '1px solid var(--primary)' : '1px solid var(--panel-border)',
          color: 'var(--text-main)',
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          fontSize: '0.95rem',
          cursor: disabled ? 'not-allowed' : 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          transition: 'all 0.2s ease',
          boxShadow: isOpen ? '0 0 0 2px rgba(100, 50, 255, 0.2)' : 'none',
          fontFamily: "'Inter', 'Noto Color Emoji', sans-serif"
        }}
      >
        <span>{selectedOption ? selectedOption.label : (placeholder || 'Select...')}</span>
        <ChevronDown size={18} style={{ 
          transition: 'transform 0.2s ease', 
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          color: isOpen ? 'var(--primary)' : 'var(--text-muted)'
        }} />
      </div>

      {typeof document !== 'undefined' && dropdownContent && createPortal(dropdownContent, document.body)}
    </div>
  );
};

export default CustomSelect;
