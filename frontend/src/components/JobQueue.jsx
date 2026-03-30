import React, { useState, useEffect } from 'react';
import { Activity, Play, RefreshCw } from 'lucide-react';

export function JobQueue({ jobs }) {

  // Aggregated calculations
  const totalJobs = jobs.length;
  const completedJobs = jobs.filter(j => j.status === 'completed').length;
  const failedJobs = jobs.filter(j => j.status === 'failed').length;
  
  const activeJobs = jobs.filter(j => !['completed', 'failed', 'cancelled', 'queued'].includes(j.status));
  const activeJob = activeJobs.length > 0 ? activeJobs[0] : null;
  const isBatchFinished = totalJobs > 0 && activeJobs.length === 0;

  return (
    <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Activity size={24} color="var(--primary)" />
          <h3 style={{ margin: 0 }}>Pipeline Overview</h3>
        </div>
        <button 
          onClick={async () => {
            const cancellable = jobs.filter(j => !['completed', 'failed', 'cancelled'].includes(j.status));
            for (const j of cancellable) {
              await fetch(`/api/jobs/${j.id}`, { method: 'DELETE' }).catch(() => {});
            }
          }}
          style={{ background: 'var(--danger)', border: 'none', padding: '0.4rem 0.8rem', borderRadius: '6px', color: 'white', cursor: 'pointer', fontSize: '0.8rem' }}>
          Cancel All Operations
        </button>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ flex: 1, background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--panel-border)', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-muted)' }}>Total Queue</h4>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text)' }}>{totalJobs}</span>
        </div>
        <div style={{ flex: 1, background: 'rgba(52, 211, 153, 0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(52, 211, 153, 0.2)', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#34d399' }}>Processed</h4>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#34d399' }}>{completedJobs}</span>
        </div>
        <div style={{ flex: 1, background: 'rgba(239, 68, 68, 0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)', textAlign: 'center' }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: '#ef4444' }}>Errors</h4>
          <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ef4444' }}>{failedJobs}</span>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto', paddingRight: '0.5rem' }}>
        <h4 style={{ margin: 0, color: 'var(--primary)', marginBottom: '0.5rem' }}>Currently Processing</h4>
        
        {isBatchFinished ? (
          <div style={{ padding: '2rem', textAlign: 'center', background: 'rgba(52, 211, 153, 0.1)', borderRadius: '12px', border: '1px solid rgba(52, 211, 153, 0.4)', marginBottom: '1rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', color: '#34d399', fontSize: '1.5rem' }}>✨ Batch Processing Complete ✨</h3>
            <p style={{ color: 'var(--text)', marginBottom: '1.5rem', fontSize: '1.1rem' }}>
              Successfully processed <strong>{completedJobs}</strong> items. <br/>
              {failedJobs > 0 && <span style={{ color: 'var(--danger)' }}><strong>{failedJobs}</strong> items failed.</span>}
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              {failedJobs > 0 && (
                <button 
                  onClick={async () => {
                    const failed = jobs.filter(j => j.status === 'failed');
                    for (const j of failed) {
                      await fetch(`/api/jobs/${j.id}/retry`, { method: 'POST' }).catch(() => {});
                    }
                  }}
                  style={{ background: 'var(--primary)', border: 'none', padding: '0.6rem 1.2rem', borderRadius: '6px', color: 'white', cursor: 'pointer', fontWeight: 'bold' }}>
                  Retry All Failed
                </button>
              )}
              <button 
                onClick={async () => {
                   const toClear = jobs.filter(j => ['completed', 'failed', 'cancelled'].includes(j.status));
                   for (const j of toClear) {
                     await fetch(`/api/jobs/${j.id}`, { method: 'DELETE' }).catch(() => {});
                   }
                }}
                style={{ background: 'transparent', border: '1px solid var(--text-muted)', padding: '0.6rem 1.2rem', borderRadius: '6px', color: 'var(--text)', cursor: 'pointer' }}>
                Clear Queue History
              </button>
            </div>
          </div>
        ) : activeJob ? (
           <div style={{ 
              background: 'rgba(255, 255, 255, 0.08)',
              padding: '1.5rem', 
              borderRadius: '12px', 
              border: '1px solid var(--primary)',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <div style={{ fontWeight: 600, fontSize: '1.1rem', wordBreak: 'break-all', paddingRight: '1rem', color: 'var(--text)' }}>
                  {activeJob.filepath.split(/[\\/]/).pop()}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span className={`status-badge status-${activeJob.status}`}>
                    {activeJob.status.toUpperCase().replace('_', ' ')}
                  </span>
                  <button 
                    onClick={() => fetch(`/api/jobs/${activeJob.id}`, { method: 'DELETE' }).catch(() => {})}
                    style={{ background: 'transparent', border: '1px solid var(--danger)', color: 'var(--danger)', borderRadius: '4px', cursor: 'pointer', padding: '2px 8px', fontSize: '0.8rem' }}>
                    Kill Task
                  </button>
                </div>
              </div>
              
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Play size={16} color="var(--primary)" />
                {activeJob.message || 'Processing...'}
              </div>
              
              <div style={{ width: '100%', background: 'rgba(0,0,0,0.3)', height: '12px', borderRadius: '6px', overflow: 'hidden', position: 'relative' }}>
                <div style={{ 
                  width: `${activeJob.progress}%`, 
                  height: '100%', 
                  background: 'var(--primary)',
                  transition: 'width 0.3s ease',
                  boxShadow: '0 0 10px var(--primary)'
                }} />
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', textAlign: 'right' }}>
                {(activeJob.progress || 0).toFixed(1)}%
              </div>
            </div>
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed var(--panel-border)' }}>
            <Activity size={32} style={{ opacity: 0.5, marginBottom: '1rem' }} />
            <p>No active jobs in the queue.</p>
          </div>
        )}

        {jobs.filter(j => j.status === 'failed').length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--danger)' }}>Failed Jobs</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {jobs.filter(j => j.status === 'failed').map(job => (
                <div key={job.id} style={{ 
                  background: 'rgba(239, 68, 68, 0.05)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(239, 68, 68, 0.2)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                  <div style={{ overflow: 'hidden', paddingRight: '1rem' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {job.filepath.split(/[\\/]/).pop()}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--danger)', marginTop: '0.25rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {job.message}
                    </div>
                  </div>
                  <button 
                    onClick={() => fetch(`/api/jobs/${job.id}/retry`, { method: 'POST' }).catch(() => {})}
                    style={{ background: 'var(--primary)', border: 'none', padding: '0.5rem 1rem', borderRadius: '6px', color: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', whiteSpace: 'nowrap' }}>
                    <RefreshCw size={16} /> Retry
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {jobs.filter(j => j.status === 'pending' || j.status.startsWith('awaiting')).length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-muted)' }}>Pending Queue</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {jobs.filter(j => j.status === 'pending' || j.status.startsWith('awaiting')).slice(0, 10).map((job, idx) => (
                <div key={job.id} style={{
                  background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--panel-border)', display: 'flex', justifyContent: 'space-between'
                }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text)' }}>
                    <span style={{color: 'var(--text-muted)', marginRight: '0.5rem'}}>#{idx+1}</span>
                    {job.filepath.split(/[\\/]/).pop()}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{job.status.replace('_', ' ')}</span>
                </div>
              ))}
              {jobs.filter(j => j.status === 'pending' || j.status.startsWith('awaiting')).length > 10 && (
                <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                  + {jobs.filter(j => j.status === 'pending' || j.status.startsWith('awaiting')).length - 10} more in queue...
                </div>
              )}
            </div>
          </div>
        )}

        {jobs.filter(j => j.status === 'completed').length > 0 && (
          <div style={{ marginTop: '1rem', paddingBottom: '1rem' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#34d399' }}>Completed Jobs</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {jobs.filter(j => j.status === 'completed').reverse().slice(0, 15).map((job, idx) => (
                <div key={job.id} style={{
                  background: 'rgba(52, 211, 153, 0.05)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(52, 211, 153, 0.2)', display: 'flex', justifyContent: 'space-between'
                }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text)' }}>
                    {job.filepath.split(/[\\/]/).pop()}
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#34d399' }}>{job.message || 'Completed'}</span>
                </div>
              ))}
              {jobs.filter(j => j.status === 'completed').length > 15 && (
                <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                  + {jobs.filter(j => j.status === 'completed').length - 15} more completed jobs hidden.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
