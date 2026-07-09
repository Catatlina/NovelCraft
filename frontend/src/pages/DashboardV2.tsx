import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Zap, TrendingUp, FileText, BookOpen, GitBranch, BarChart3, Sparkles, Clock, ArrowRight, Search } from 'lucide-react';
import { api } from '@/api/client';
import { useProjectStore } from '@/store/projectStore';
import '@/styles/novelcraft-theme.css';

export default function DashboardV2() {
  const nav = useNavigate();
  const [ops, setOps] = useState<any>({});
  const [projects, setProjects] = useState<any[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [newGenre, setNewGenre] = useState('修真');
  const [showCreate, setShowCreate] = useState(false);
  const setProjectId = useProjectStore(s => s.setSelectedProjectId);

  useEffect(() => { load(); }, []);
  const load = async () => {
    try { const [o, p] = await Promise.all([api('/ops/dashboard'), api('/projects')]); setOps(o); setProjects(p || []); } catch {}
  };

  const create = async () => {
    if (!newTitle.trim()) return;
    try {
      const p = await api('/projects', 'POST', { title: newTitle.trim(), genre: newGenre });
      setShowCreate(false); setNewTitle('');
      if (p?.id) { setProjectId(p.id); nav(`/write/${p.id}`); }
      load();
    } catch {}
  };

  const selectAndGo = (pid: string, dest: string) => { setProjectId(pid); nav(dest); };

  return (
    <div>
      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginBottom: 24 }}>
        {[
          { label: '总字数', val: ops?.total_words?.toLocaleString() || '0', icon: FileText },
          { label: '项目数', val: ops?.project_count || projects.length, icon: BookOpen },
          { label: '活跃项目', val: ops?.active_count || 0, icon: Zap },
          { label: '本月新增', val: ops?.monthly_new || 0, icon: TrendingUp },
        ].map(k => (
          <div key={k.label} className="nc-card nc-fade-in" style={{ textAlign: 'center', padding: '16px 12px' }}>
            <k.icon size={20} color="var(--nc-text-dim)" />
            <div className="nc-kpi-value" style={{ fontSize: 28, marginTop: 6 }}>{k.val}</div>
            <div className="nc-kpi-label">{k.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Projects */}
        <div className="nc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 className="nc-section-title" style={{ marginBottom: 0 }}><BookOpen size={16} /> 项目列表</h2>
            <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={() => setShowCreate(true)}>
              <Plus size={14} /> 新建
            </button>
          </div>
          {showCreate && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <input className="nc-input" placeholder="项目名称" value={newTitle} onChange={e => setNewTitle(e.target.value)}
                style={{ flex: 1, padding: '6px 10px', fontSize: 13 }}
                onKeyDown={e => e.key === 'Enter' && create()} />
              <select className="nc-input" value={newGenre} onChange={e => setNewGenre(e.target.value)}
                style={{ width: 100, padding: '6px 8px', fontSize: 13 }}>
                {['修真','玄幻','都市','科幻','历史','悬疑','游戏','轻小说'].map(g => <option key={g}>{g}</option>)}
              </select>
              <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={create}>创建</button>
            </div>
          )}
          {projects.map(p => (
            <div key={p.id} className="nc-card" onClick={() => selectAndGo(p.id, `/write/${p.id}`)}
              style={{ padding: '12px 14px', marginBottom: 8, cursor: 'pointer' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{p.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--nc-text-dim)', marginTop: 2 }}>
                    {p.genre} · {p.total_chapters || 0}章 · {(p.total_words || 0).toLocaleString()}字
                  </div>
                </div>
                <span className={`nc-tag ${p.status === 'writing' ? 'nc-tag-primary' : 'nc-tag-accent'}`}>
                  {p.status || 'draft'}
                </span>
              </div>
            </div>
          ))}
          {projects.length === 0 && (
            <p style={{ textAlign: 'center', color: 'var(--nc-text-dim)', padding: 20 }}>暂无项目，点击"新建"或去"快速开始"创建</p>
          )}
        </div>

        {/* Quick actions + Status */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="nc-card">
            <h2 className="nc-section-title"><Zap size={16} /> 快捷入口</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { label: '快速开始', icon: Sparkles, desc: '一句话灵感生成小说', path: '/quick-start' },
                { label: '扫榜分析', icon: TrendingUp, desc: 'AI 推荐趋势方向', path: '/trends' },
                { label: '拆文学习', icon: FileText, desc: '拆解爆款写法', path: '/analytics' },
                { label: '配置中心', icon: BarChart3, desc: '管理 API Key 等', path: '/config' },
              ].map(a => (
                <div key={a.label} className="nc-card" onClick={() => nav(a.path)}
                  style={{ padding: 12, cursor: 'pointer', textAlign: 'center' }}>
                  <a.icon size={22} color="var(--nc-primary)" />
                  <div style={{ fontSize: 12, fontWeight: 600, marginTop: 4 }}>{a.label}</div>
                  <div style={{ fontSize: 10, color: 'var(--nc-text-dim)' }}>{a.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="nc-card">
            <h2 className="nc-section-title"><Clock size={16} /> 最近活动</h2>
            <p style={{ color: 'var(--nc-text-dim)', fontSize: 13, textAlign: 'center', padding: 20 }}>
              {ops?.recent_activity || '暂无最近活动，去快速开始创建第一本小说吧'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
