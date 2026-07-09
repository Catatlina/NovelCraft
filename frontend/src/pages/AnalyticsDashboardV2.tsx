import React, { useState, useEffect } from 'react';
import { BarChart3, RefreshCw } from 'lucide-react';
import { api } from '@/api/client';
import '@/styles/novelcraft-theme.css';

export default function AnalyticsDashboardV2() {
  const [ops, setOps] = useState<any>({});
  const [analytics, setAnalytics] = useState<any[]>([]);

  useEffect(() => { load(); }, []);
  const load = async () => {
    try {
      const [o, a] = await Promise.all([api('/ops/dashboard'), api('/analytics')]);
      setOps(o); setAnalytics(a || []);
    } catch {}
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1 className="nc-page-title" style={{ marginBottom: 0 }}><BarChart3 size={22} style={{ marginRight: 8, display: 'inline' }} />数据分析</h1>
        <button className="nc-btn nc-btn-ghost nc-btn-sm" onClick={load}><RefreshCw size={14} /> 刷新</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 24 }}>
        {[
          { label: '总字数', val: (ops?.total_words || 0).toLocaleString() },
          { label: '项目数', val: ops?.project_count || 0 },
          { label: '活跃项目', val: ops?.active_count || 0 },
          { label: '本月生成', val: ops?.monthly_new || 0 },
          { label: '总章节', val: ops?.total_chapters || 0 },
          { label: '平均质量', val: ops?.avg_quality || '-' },
        ].map(k => (
          <div key={k.label} className="nc-card nc-fade-in" style={{ textAlign: 'center', padding: 20 }}>
            <div className="nc-kpi-value">{k.val}</div>
            <div className="nc-kpi-label">{k.label}</div>
          </div>
        ))}
      </div>

      {analytics.length > 0 && (
        <div className="nc-card" style={{ padding: 16 }}>
          <h3 className="nc-section-title">事件日志</h3>
          {analytics.slice(0, 20).map((e: any, i: number) => (
            <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid var(--nc-border)', fontSize: 12 }}>
              <span style={{ color: 'var(--nc-accent)' }}>{e.event_type}</span>
              <span style={{ color: 'var(--nc-text-dim)', marginLeft: 12 }}>{e.created_at}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
