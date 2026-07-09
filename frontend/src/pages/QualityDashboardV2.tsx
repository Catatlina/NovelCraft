import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { BarChart3, RefreshCw, Edit3, Star } from 'lucide-react';
import { api } from '@/api/client';
import '@/styles/novelcraft-theme.css';

const DIMENSIONS = ['consistency','ai_detection','pacing','ooc','thrill_density','dialogue_quality','ending_hook'];
const DIM_LABELS: Record<string,string> = {
  consistency:'一致性',ai_detection:'AI痕迹',pacing:'节奏',ooc:'人物OOC',
  thrill_density:'爽点密度',dialogue_quality:'对话质量',ending_hook:'结尾钩子',
};

export default function QualityDashboardV2() {
  const { projectId } = useParams<{ projectId: string }>();
  const [chapters, setChapters] = useState<any[]>([]);
  const [reviews, setReviews] = useState<Record<string,any>>({});
  const [reviewing, setReviewing] = useState<Record<string,boolean>>({});
  const [rewriting, setRewriting] = useState<Record<string,boolean>>({});

  useEffect(() => { load(); }, [projectId]);
  const load = async () => {
    try {
      const r = await api(`/projects/${projectId}/chapters`);
      const chs = r?.chapters || [];
      setChapters(chs);
      for (const ch of chs.slice(0, 10)) {
        try { const q = await api(`/quality/${ch.id}/reviews`); setReviews(prev => ({...prev, [ch.id]: q?.[0] || null})); } catch {}
      }
    } catch {}
  };

  const runReview = async (chId: string) => {
    setReviewing(prev => ({...prev, [chId]: true}));
    try {
      const ch = chapters.find(c => c.id === chId);
      await api(`/quality/${chId}/review`, 'POST', { chapter: ch?.content || '', outline: '' });
      const q = await api(`/quality/${chId}/reviews`);
      setReviews(prev => ({...prev, [chId]: q?.[0] || null}));
    } catch {} finally { setReviewing(prev => ({...prev, [chId]: false})); }
  };

  const runRewrite = async (chId: string) => {
    setRewriting(prev => ({...prev, [chId]: true}));
    try { await api(`/quality/${chId}/rewrite`, 'POST', {}); load(); }
    catch {} finally { setRewriting(prev => ({...prev, [chId]: false})); }
  };

  return (
    <div>
      <h1 className="nc-page-title"><BarChart3 size={22} style={{ marginRight: 8, display: 'inline' }} />质量面板</h1>

      {chapters.map(ch => {
        const rev = reviews[ch.id];
        return (
          <div key={ch.id} className="nc-card" style={{ marginBottom: 14, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <h3 style={{ fontSize: 15, fontWeight: 600 }}>第{ch.chapter_num}章 {ch.title}</h3>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {rev && (
                  <span style={{ fontSize: 24, fontWeight: 800,
                    color: rev.overall_score >= 80 ? 'var(--nc-success)' : rev.overall_score >= 60 ? 'var(--nc-warning)' : 'var(--nc-danger)' }}>
                    {rev.overall_score}
                  </span>
                )}
                <button className="nc-btn nc-btn-secondary nc-btn-sm" onClick={() => runReview(ch.id)}
                  disabled={reviewing[ch.id]}>
                  <RefreshCw size={14} className={reviewing[ch.id] ? 'nc-spinner' : ''} />
                  {reviewing[ch.id] ? '审查中' : '审查'}
                </button>
                <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={() => runRewrite(ch.id)}
                  disabled={rewriting[ch.id]}>
                  <Edit3 size={14} /> 改写
                </button>
              </div>
            </div>

            {rev && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8 }}>
                {DIMENSIONS.map(d => {
                  const score = rev.dimensions?.[d] || 0;
                  return (
                    <div key={d} style={{ textAlign: 'center', padding: 8,
                      background: score >= 80 ? 'rgba(0,230,118,0.08)' : score >= 60 ? 'rgba(255,171,64,0.08)' : 'rgba(255,82,82,0.08)',
                      borderRadius: 8 }}>
                      <div style={{ fontSize: 20, fontWeight: 700,
                        color: score >= 80 ? 'var(--nc-success)' : score >= 60 ? 'var(--nc-warning)' : 'var(--nc-danger)' }}>
                        {score}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--nc-text-dim)' }}>{DIM_LABELS[d]}</div>
                    </div>
                  );
                })}
              </div>
            )}

            {!rev && <p style={{ fontSize: 12, color: 'var(--nc-text-dim)' }}>点击"审查"运行 7 维质量检测</p>}
          </div>
        );
      })}
    </div>
  );
}
