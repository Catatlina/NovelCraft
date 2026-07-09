import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Globe, Send, History, FileText } from 'lucide-react';
import { api } from '@/api/client';
import '@/styles/novelcraft-theme.css';

const LANGUAGES = [
  { code: 'en', label: 'English (Webnovel)' },
  { code: 'ja', label: '日本語 (小説家になろう)' },
  { code: 'ko', label: '한국어 (카카오페이지)' },
];

export default function TranslatePageV2() {
  const { projectId } = useParams<{ projectId: string }>();
  const [chapters, setChapters] = useState<any[]>([]);
  const [activeCh, setActiveCh] = useState<any>(null);
  const [targetLang, setTargetLang] = useState('en');
  const [translated, setTranslated] = useState('');
  const [translating, setTranslating] = useState(false);
  const [executions, setExecutions] = useState<any[]>([]);

  useEffect(() => { loadChapters(); loadHistory(); }, [projectId]);
  const loadChapters = async () => {
    try { const r = await api(`/projects/${projectId}/chapters`); setChapters(r?.chapters || []); } catch {}
  };
  const loadHistory = async () => {
    try { const r = await api(`/publish-executions/${projectId}`); setExecutions(r || []); } catch {}
  };

  const translate = async () => {
    if (!activeCh) return;
    setTranslating(true);
    try {
      const r = await api(`/translate/${activeCh.id}`, 'POST', { target_lang: targetLang });
      setTranslated(r?.content || r?.translated || '');
    } catch {} finally { setTranslating(false); }
  };

  const publish = async () => {
    if (!activeCh || !translated) return;
    try { await api(`/publish-executions/${projectId}/execute`, 'POST', { chapter_id: activeCh.id }); loadHistory(); }
    catch {}
  };

  return (
    <div>
      <h1 className="nc-page-title"><Globe size={22} style={{ marginRight: 8, display: 'inline' }} />翻译发布</h1>

      <div className="nc-grid-2" style={{ gap: 14 }}>
        {/* Left: source + translate */}
        <div>
          <div className="nc-card" style={{ padding: 16, marginBottom: 14 }}>
            <h3 className="nc-section-title"><FileText size={16} /> 选择章节</h3>
            <select className="nc-input" style={{ marginBottom: 12 }}
              value={activeCh?.id || ''} onChange={e => {
                const ch = chapters.find(c => c.id === e.target.value);
                setActiveCh(ch); setTranslated('');
              }}>
              <option value="">-- 选择章节 --</option>
              {chapters.map((c: any) => (
                <option key={c.id} value={c.id}>第{c.chapter_num}章 {c.title} ({c.word_count}字)</option>
              ))}
            </select>
            {activeCh && (
              <div style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, color: 'var(--nc-text-dim)',
                padding: 10, background: 'rgba(255,255,255,0.02)', borderRadius: 6, marginBottom: 12 }}>
                {(activeCh.content || '').slice(0, 800)}...
              </div>
            )}
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', display: 'block', marginBottom: 4 }}>目标语言</label>
              <select className="nc-input" value={targetLang} onChange={e => setTargetLang(e.target.value)}>
                {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="nc-btn nc-btn-primary" onClick={translate} disabled={translating || !activeCh}>
                {translating ? '翻译中...' : '翻译'}
              </button>
              <button className="nc-btn nc-btn-secondary" onClick={publish} disabled={!translated}>
                <Send size={14} /> 发布
              </button>
            </div>
          </div>

          {translated && (
            <div className="nc-card" style={{ padding: 16 }}>
              <h3 className="nc-section-title">📖 翻译结果</h3>
              <pre style={{ fontSize: 12, color: 'var(--nc-text)', whiteSpace: 'pre-wrap', maxHeight: 400, overflow: 'auto' }}>{translated}</pre>
            </div>
          )}
        </div>

        {/* Right: history */}
        <div className="nc-card" style={{ padding: 16 }}>
          <h3 className="nc-section-title"><History size={16} /> 发布历史</h3>
          {executions.map((e: any) => (
            <div key={e.id} className="nc-card" style={{ padding: 10, marginBottom: 8, fontSize: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{e.chapter_id?.slice(0, 8)}...</span>
                <span className={`nc-tag ${e.status === 'success' ? 'nc-tag-success' : 'nc-tag-primary'}`}>
                  {e.status}
                </span>
              </div>
            </div>
          ))}
          {executions.length === 0 && (
            <p style={{ fontSize: 12, color: 'var(--nc-text-dim)', textAlign: 'center', padding: 20 }}>暂无发布记录</p>
          )}
        </div>
      </div>
    </div>
  );
}
