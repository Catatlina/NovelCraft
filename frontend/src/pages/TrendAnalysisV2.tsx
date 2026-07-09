import React, { useState } from 'react';
import { TrendingUp, Search, Zap, BookOpen } from 'lucide-react';
import { api } from '@/api/client';
import '@/styles/novelcraft-theme.css';

const PLATFORMS = ['qidian','fanqie','jinjiang','zongheng','webnovel','royalroad'];
const CATEGORIES = ['热门','修真','玄幻','都市','科幻','历史','悬疑','游戏','轻小说'];

export default function TrendAnalysisV2() {
  const [platform, setPlatform] = useState('qidian');
  const [category, setCategory] = useState('');
  const [extra, setExtra] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const run = async () => {
    setLoading(true); setResult(null);
    try {
      const r = await api('/projects/auto', 'POST', { platform, category, extra_prompt: extra });
      setResult(r);
    } catch {} finally { setLoading(false); }
  };

  return (
    <div>
      <h1 className="nc-page-title"><TrendingUp size={22} style={{ marginRight: 8, display: 'inline' }} />爆款分析</h1>

      <div className="nc-card" style={{ padding: 20, marginBottom: 20 }}>
        <div className="nc-grid-2" style={{ marginBottom: 14 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', display: 'block', marginBottom: 4 }}>平台</label>
            <select className="nc-input" value={platform} onChange={e => setPlatform(e.target.value)}>
              {PLATFORMS.map(p => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', display: 'block', marginBottom: 4 }}>题材</label>
            <select className="nc-input" value={category} onChange={e => setCategory(e.target.value)}>
              <option value="">全部</option>
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', display: 'block', marginBottom: 4 }}>额外要求</label>
          <input className="nc-input" placeholder="如：写一个系统流爽文..." value={extra} onChange={e => setExtra(e.target.value)} />
        </div>
        <button className="nc-btn nc-btn-primary" onClick={run} disabled={loading}
          style={{ width: '100%', padding: 12 }}>
          <Zap size={16} className={loading ? 'nc-spinner' : ''} style={{ marginRight: 8 }} />
          {loading ? 'AI 分析中...' : '扫榜 + 自动生成黄金三章'}
        </button>
      </div>

      {result && (
        <div className="nc-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="nc-card" style={{ padding: 16 }}>
            <h3 className="nc-section-title"><BookOpen size={16} /> 书名：{result.title}</h3>
          </div>
          {result.scan && (
            <div className="nc-card" style={{ padding: 16 }}>
              <h3 className="nc-section-title">📊 扫榜分析</h3>
              <pre style={{ fontSize: 12, color: 'var(--nc-text-dim)', whiteSpace: 'pre-wrap', maxHeight: 300, overflow: 'auto' }}>{result.scan}</pre>
            </div>
          )}
          {result.plan && (
            <div className="nc-card" style={{ padding: 16 }}>
              <h3 className="nc-section-title">📋 全书规划</h3>
              <pre style={{ fontSize: 12, color: 'var(--nc-text-dim)', whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto' }}>{result.plan}</pre>
            </div>
          )}
          {result.chapters && (
            <div className="nc-card" style={{ padding: 16 }}>
              <h3 className="nc-section-title">📖 已生成 {result.chapters.length} 章</h3>
              {result.chapters.map((c: any) => (
                <div key={c.chapter_num} className="nc-card" style={{ padding: 10, marginBottom: 8, fontSize: 12 }}>
                  <div style={{ fontWeight: 600 }}>第{c.chapter_num}章 {c.title} ({c.word_count}字)</div>
                  <div style={{ color: 'var(--nc-text-dim)', marginTop: 4 }}>{c.content_preview}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
