import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import {
  BookOpen, Users, GitBranch, FileText, Sparkles,
  Send, RotateCcw, AlertTriangle, CheckCircle,
  ChevronLeft, ChevronRight, Clock, Zap, BarChart3
} from 'lucide-react';
import '@/styles/novelcraft-theme.css';

interface Chapter { id: string; chapter_num: number; title: string; content: string; summary: string; word_count: number; status: string; }
interface Project { id: string; title: string; genre: string; overall_outline: string; characters_json: any[]; chapter_tree: any[]; total_chapters: number; total_words: number; }

export default function WritingWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [activeChapter, setActiveChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [revising, setRevising] = useState(false);
  const [aiPanel, setAiPanel] = useState<'review' | 'threads' | 'suggest'>('review');
  const [review, setReview] = useState<any>(null);
  const [threadResult, setThreadResult] = useState<any>(null);
  const [suggestion, setSuggestion] = useState('');
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const saveTimer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { loadProject(); }, [projectId]);

  const loadProject = async () => {
    try {
      const [p, chs] = await Promise.all([
        api(`/projects/${projectId}`),
        api(`/projects/${projectId}/chapters`),
      ]);
      setProject(p);
      setChapters(chs?.chapters || []);
      if (chs?.chapters?.length > 0) selectChapter(chs.chapters[0]);
    } catch { navigate('/'); }
  };

  const selectChapter = async (ch: Chapter) => {
    setActiveChapter(ch);
    setContent(ch.content || '');
    setReview(null); setThreadResult(null);
    try {
      const q = await api(`/quality/${ch.id}/reviews`);
      setReview(q?.[0] || null);
    } catch {}
  };

  const autoSave = useCallback((val: string) => {
    setContent(val);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      if (!activeChapter) return;
      setSaving(true);
      try { await api(`/chapters/${activeChapter.id}`, 'PUT', { content: val }); }
      catch {}
      setSaving(false);
    }, 1500);
  }, [activeChapter]);

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await api(`/projects/${projectId}/chapters/generate`, 'POST', { mode: 'continue' });
      await loadProject();
      if (r?.chapter) selectChapter(r.chapter);
    } catch {} finally { setGenerating(false); }
  };

  const runReview = async () => {
    if (!activeChapter) return;
    setAiPanel('review');
    try {
      const r = await api(`/quality/${activeChapter.id}/review`, 'POST', {
        chapter: content, outline: project?.overall_outline || '',
      });
      setReview(r);
    } catch {}
  };

  const runAutoRevise = async () => {
    if (!activeChapter) return;
    setRevising(true);
    try {
      const r = await api('/projects/auto-revise', 'POST', {
        chapter_content: content, chapter_num: activeChapter.chapter_num,
        context: { characters: project?.characters_json || [] },
      });
      setContent(r.final_content);
      setReview({ overall_score: r.final_score, iterations: r.iterations });
    } catch {} finally { setRevising(false); }
  };

  const runThreads = async () => {
    if (!activeChapter) return;
    setAiPanel('threads');
    try {
      const r = await api('/projects/story-threads', 'POST', {
        threads: [{ name: '主线', status: 'active', next_event: '' },
                  { name: '支线', status: 'active', next_event: '' }],
        chapter_content: content, chapter_num: activeChapter.chapter_num,
      });
      setThreadResult(r);
    } catch {}
  };

  const runSuggestion = async () => {
    setAiPanel('suggest');
    setSuggestion('思考中...');
    try {
      const r = await fetch('/api/v1/tools/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: content.slice(-500), genre: project?.genre }),
      });
      const d = await (r.ok ? r.json() : { suggestion: 'AI暂时无法响应' });
      setSuggestion(d.suggestion || d.detail || '暂无建议');
    } catch { setSuggestion('请求失败'); }
  };

  if (!project) return <div className="nc-page nc-spinner">加载中...</div>;

  return (
    <div className="nc-main">
      {/* Top bar */}
      <div className="nc-header" style={{ padding: '0 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="nc-btn nc-btn-ghost nc-btn-sm" onClick={() => navigate('/')}>
            <ChevronLeft size={16} /> 返回
          </button>
          <span style={{ fontWeight: 700, fontSize: 15 }}>{project.title}</span>
          <span className="nc-tag nc-tag-primary">{project.genre}</span>
          <span style={{ fontSize: 12, color: 'var(--nc-text-dim)' }}>
            {project.total_chapters}章 · {(project.total_words || 0).toLocaleString()}字
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {saving && <span style={{ fontSize: 11, color: 'var(--nc-accent)' }}>保存中...</span>}
          <button className="nc-btn nc-btn-secondary nc-btn-sm" onClick={runReview}>
            <BarChart3 size={14} /> 审查
          </button>
          <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={runAutoRevise} disabled={revising}>
            <RotateCcw size={14} className={revising ? 'nc-spinner' : ''} />
            {revising ? '修改中' : '自动返工'}
          </button>
          <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={generate} disabled={generating}>
            <Sparkles size={14} className={generating ? 'nc-spinner' : ''} />
            {generating ? '生成中' : '续写'}
          </button>
        </div>
      </div>

      {/* Main layout */}
      <div style={{ display: 'flex', height: 'calc(100vh - var(--nc-header))', marginTop: 'var(--nc-header)' }}>
        {/* Left panel: Chapter tree */}
        {showLeftPanel && (
          <div style={{ width: 220, borderRight: '1px solid var(--nc-border)', overflow: 'auto', padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)' }}>章节目录</span>
              <button className="nc-btn nc-btn-ghost nc-btn-xs" onClick={() => setShowLeftPanel(false)}>
                <ChevronLeft size={12} />
              </button>
            </div>
            {chapters.map(ch => (
              <div key={ch.id}
                onClick={() => selectChapter(ch)}
                style={{
                  padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
                  background: activeChapter?.id === ch.id ? 'rgba(255,107,53,0.12)' : 'transparent',
                  color: activeChapter?.id === ch.id ? 'var(--nc-primary)' : 'var(--nc-text-dim)',
                  marginBottom: 2,
                }}
              >
                <div style={{ fontWeight: 500 }}>第{ch.chapter_num}章</div>
                <div style={{ fontSize: 11, opacity: 0.7 }}>{ch.title?.replace(/^第\d+章\s*/, '')}</div>
                <div style={{ fontSize: 10, opacity: 0.5 }}>{ch.word_count}字</div>
              </div>
            ))}
          </div>
        )}

        {/* Center: Editor */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {!showLeftPanel && (
            <button className="nc-btn nc-btn-ghost nc-btn-xs" style={{ margin: 4 }}
              onClick={() => setShowLeftPanel(true)}>
              <ChevronRight size={12} /> 目录
            </button>
          )}
          <div style={{ flex: 1, padding: '16px 24px', overflow: 'auto' }}>
            {activeChapter && (
              <>
                <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <h2 style={{ fontSize: 18, fontWeight: 700 }}>
                    第{activeChapter.chapter_num}章 {activeChapter.title}
                  </h2>
                  <span style={{ fontSize: 11, color: 'var(--nc-text-dim)' }}>
                    {activeChapter.word_count}字 · {activeChapter.status}
                  </span>
                </div>
                <textarea
                  value={content}
                  onChange={e => autoSave(e.target.value)}
                  style={{
                    width: '100%', minHeight: 'calc(100vh - 200px)',
                    background: 'transparent', border: 'none',
                    color: 'var(--nc-text)', fontSize: 15, lineHeight: 2,
                    fontFamily: "'Georgia', 'PingFang SC', serif",
                    resize: 'none', outline: 'none', padding: 0,
                  }}
                  placeholder="开始在右侧AI面板生成第一章..."
                />
              </>
            )}
          </div>
        </div>

        {/* Right panel: AI assistant */}
        {showRightPanel && (
          <div style={{ width: 280, borderLeft: '1px solid var(--nc-border)', overflow: 'auto', padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)' }}>AI 助手</span>
              <button className="nc-btn nc-btn-ghost nc-btn-xs" onClick={() => setShowRightPanel(false)}>
                <ChevronRight size={12} />
              </button>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
              {[
                { id: 'review', label: '审查', icon: BarChart3 },
                { id: 'threads', label: '剧情', icon: GitBranch },
                { id: 'suggest', label: '建议', icon: Zap },
              ].map(t => (
                <button key={t.id}
                  className={`nc-btn nc-btn-${aiPanel === t.id ? 'primary' : 'ghost'} nc-btn-xs`}
                  onClick={() => { setAiPanel(t.id as any); t.id === 'review' && runReview(); t.id === 'threads' && runThreads(); }}>
                  <t.icon size={12} /> {t.label}
                </button>
              ))}
            </div>

            {/* Review panel */}
            {aiPanel === 'review' && review && (
              <div className="nc-fade-in">
                <div className="nc-card" style={{ padding: 12, marginBottom: 8 }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 32, fontWeight: 800,
                      color: review.overall_score >= 80 ? 'var(--nc-success)' : 'var(--nc-warning)' }}>
                      {review.overall_score || review.final_score || '-'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--nc-text-dim)' }}>综合评分</div>
                  </div>
                </div>
                {review.issues && (
                  <div style={{ fontSize: 12 }}>
                    {review.issues.slice(0, 8).map((i: any, idx: number) => (
                      <div key={idx} style={{
                        padding: '6px 8px', borderRadius: 4, marginBottom: 4,
                        background: i.severity === 'error' ? 'rgba(255,82,82,0.1)' : 'rgba(255,171,64,0.08)',
                      }}>
                        <span style={{ color: i.severity === 'error' ? 'var(--nc-danger)' : 'var(--nc-warning)' }}>
                          {i.severity === 'error' ? '!' : '~'}
                        </span> {i.description}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Threads panel */}
            {aiPanel === 'threads' && threadResult && (
              <div className="nc-fade-in" style={{ fontSize: 12 }}>
                <div className="nc-card" style={{ padding: 10, marginBottom: 8 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>剧情推进</div>
                  {(threadResult.threads?.threads_advanced || []).map((t: string, i: number) => (
                    <div key={i} style={{ color: 'var(--nc-success)' }}>+ {t}</div>
                  ))}
                  {(threadResult.threads?.threads_stalled || []).map((t: string, i: number) => (
                    <div key={i} style={{ color: 'var(--nc-warning)' }}>- {t} (未推进)</div>
                  ))}
                </div>
                <div className="nc-card" style={{ padding: 10 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>节奏分析</div>
                  <div>动作 {threadResult.pacing?.action_ratio}%</div>
                  <div>对话 {threadResult.pacing?.dialogue_ratio}%</div>
                  <div>冲突强度 {threadResult.pacing?.conflict_intensity}/10</div>
                  <div style={{ color: 'var(--nc-accent)' }}>{threadResult.pacing?.readability}</div>
                </div>
              </div>
            )}

            {/* Suggest panel */}
            {aiPanel === 'suggest' && (
              <div className="nc-fade-in nc-card" style={{ padding: 10, fontSize: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>AI 续写建议</div>
                <div style={{ color: 'var(--nc-text-dim)', whiteSpace: 'pre-wrap' }}>{suggestion}</div>
                <button className="nc-btn nc-btn-primary nc-btn-xs" style={{ marginTop: 8 }} onClick={runSuggestion}>
                  <RefreshCcw size={12} /> 重新建议
                </button>
              </div>
            )}

            {!showRightPanel && (
              <button className="nc-btn nc-btn-ghost nc-btn-xs" style={{ margin: 4 }}
                onClick={() => setShowRightPanel(true)}>
                <ChevronLeft size={12} /> AI助手
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function RefreshCcw({ size, className }: any) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
  </svg>;
}
