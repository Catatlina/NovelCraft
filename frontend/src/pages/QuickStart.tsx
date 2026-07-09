import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Zap, RefreshCw, BookOpen, FileText, ChevronRight } from 'lucide-react';
import { api } from '@/api/client';

const GENRES = ['修真','玄幻','都市','科幻','历史','悬疑','游戏','轻小说','女频'];

export default function QuickStart() {
  const nav = useNavigate();
  const [idea, setIdea] = useState('');
  const [genre, setGenre] = useState('修真');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!idea.trim() || idea.trim().length < 5) { setError('请输入至少5个字的灵感描述'); return; }
    setLoading(true); setError(''); setResult(null);
    try { setResult(await api('/projects/quick-start', 'POST', { idea: idea.trim(), genre })); }
    catch (e: any) { setError(e?.detail || '生成失败，请重试'); }
    finally { setLoading(false); }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white flex items-center justify-center gap-3">
          <Sparkles className="text-primary-500" size={32} /> 快速开始
        </h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">输入一句话灵感，AI 自动生成书名、大纲、细纲、第一章</p>
      </div>

      {/* Input card */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
        <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">💡 写下一句话灵感</label>
        <textarea className="mb-3 min-h-24 w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          placeholder="例如：修真界数学老师用微积分破阵、重生为小师妹的反派保镖..."
          value={idea} onChange={e => setIdea(e.target.value)} disabled={loading} />

        <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">📚 选择题材</label>
        <div className="mb-4 flex flex-wrap gap-2">
          {GENRES.map(g => (
            <button key={g} disabled={loading}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                genre === g ? 'bg-primary-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'}`}
              onClick={() => setGenre(g)}>{g}</button>
          ))}
        </div>

        <button className="btn-primary w-full" onClick={handleGenerate} disabled={loading || !idea.trim()}>
          {loading ? <span className="flex items-center justify-center gap-2"><RefreshCw size={18} className="animate-spin"/>生成中...</span>
                   : <span className="flex items-center justify-center gap-2"><Zap size={18}/>一键生成</span>}
        </button>
        {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold"><BookOpen size={20} className="text-primary-500"/>可选书名</h2>
            <div className="flex flex-wrap gap-3">
              {(result.titles||[]).map((t:string,i:number)=><span key={i} className={`rounded-full px-4 py-2 text-sm font-semibold ${t===result.selected_title?'bg-primary-500 text-white':'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}`}>{t}</span>)}
            </div>
          </div>
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold"><FileText size={20} className="text-primary-500"/>简介</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">{result.synopsis}</p>
          </div>
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
            <h2 className="mb-3 text-lg font-semibold">📚 全书大纲（{result.outline?.length||0}卷）</h2>
            {result.outline?.map((vol:any)=>(<div key={vol.volume} className="mb-3 border-l-4 border-primary-300 pl-4"><h3 className="font-semibold">第{vol.volume}卷：{vol.title}</h3><p className="text-xs text-gray-500">第{vol.start_chapter}-{vol.end_chapter}章 · {vol.theme}</p><ul className="mt-1 list-inside list-disc text-sm text-gray-600 dark:text-gray-400">{(vol.events||[]).map((e:string,i:number)=><li key={i}>{e}</li>)}</ul></div>))}
          </div>
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
            <h2 className="mb-3 text-lg font-semibold">📖 第一章预览（{result.first_chapter?.word_count}字）</h2>
            <div className="max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4 text-sm leading-relaxed text-gray-700 dark:bg-gray-800 dark:text-gray-300">{result.first_chapter?.content}</div>
          </div>
          <div className="flex gap-3">
            <button className="btn-primary flex-1" onClick={()=>nav(`/write/${result.project_id}`)}>进入创作工作台 <ChevronRight size={18}/></button>
            <button className="btn-secondary" onClick={()=>{setResult(null);setIdea('')}}>重新开始</button>
          </div>
        </div>
      )}
    </div>
  );
}
