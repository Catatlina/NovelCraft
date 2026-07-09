import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Network, Plus, CheckCircle, Clock, AlertTriangle, Send } from 'lucide-react';
import { api } from '@/api/client';
import '@/styles/novelcraft-theme.css';

export default function ForeshadowBoardV2() {
  const { projectId } = useParams<{ projectId: string }>();
  const [items, setItems] = useState<any[]>([]);
  const [newDesc, setNewDesc] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { load(); }, [projectId]);
  const load = async () => {
    try { const r = await api(`/foreshadows?project_id=${projectId}`); setItems(r || []); } catch {}
  };

  const create = async () => {
    if (!newDesc.trim()) return;
    setLoading(true);
    try { await api('/foreshadows', 'POST', { project_id: projectId, description: newDesc.trim() }); setNewDesc(''); load(); }
    catch {} finally { setLoading(false); }
  };

  const resolve = async (id: string) => {
    try { await api(`/foreshadows/${id}/payoff`, 'POST', {}); load(); } catch {}
  };

  const cols = {
    planted: items.filter(i => i.status === 'planted'),
    resolved: items.filter(i => i.status === 'resolved'),
    overdue: items.filter(i => i.status === 'overdue'),
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="nc-page-title" style={{ marginBottom: 0 }}><Network size={22} style={{ marginRight: 8, display: 'inline' }} />伏笔看板</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <input className="nc-input" style={{ width: 260, padding: '6px 10px', fontSize: 13 }}
            placeholder="新伏笔描述..." value={newDesc}
            onChange={e => setNewDesc(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && create()} />
          <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={create} disabled={loading}>
            <Plus size={14} /> 添加
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
        {[
          { key: 'planted', label: '已埋设', icon: Clock, color: 'var(--nc-warning)', items: cols.planted },
          { key: 'resolved', label: '已回收', icon: CheckCircle, color: 'var(--nc-success)', items: cols.resolved },
          { key: 'overdue', label: '超期未收', icon: AlertTriangle, color: 'var(--nc-danger)', items: cols.overdue },
        ].map(col => (
          <div key={col.key} className="nc-card" style={{ padding: 12 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: col.color, marginBottom: 10 }}>
              <col.icon size={14} style={{ marginRight: 4, display: 'inline' }} />
              {col.label} ({col.items.length})
            </h3>
            {col.items.map(i => (
              <div key={i.id} className="nc-card" style={{ padding: 10, marginBottom: 6, fontSize: 12 }}>
                <div style={{ marginBottom: 4 }}>{i.description}</div>
                <div style={{ fontSize: 10, color: 'var(--nc-text-dim)' }}>
                  {i.planted_chapter ? `第${i.planted_chapter}章埋设` : ''}
                  {i.resolved_chapter ? ` · 第${i.resolved_chapter}章回收` : ''}
                </div>
                {col.key === 'planted' && (
                  <button className="nc-btn nc-btn-primary nc-btn-xs" style={{ marginTop: 6 }}
                    onClick={() => resolve(i.id)}>
                    <Send size={10} /> 标记回收
                  </button>
                )}
              </div>
            ))}
            {col.items.length === 0 && (
              <p style={{ fontSize: 12, color: 'var(--nc-text-dim)', textAlign: 'center', padding: 12 }}>暂无</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
