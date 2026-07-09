import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, BookOpen, RefreshCw, Zap, FileText, ChevronRight } from 'lucide-react';
import { api } from '@/api/client';

const GENRES = ['修真', '玄幻', '都市', '科幻', '历史', '悬疑', '游戏', '轻小说', '女频'];

export default function QuickStartPage() {
  const navigate = useNavigate();
  const [idea, setIdea] = useState('');
  const [genre, setGenre] = useState('修真');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!idea.trim() || idea.trim().length < 5) {
      setError('请输入至少5个字的灵感描述');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await api('/projects/quick-start', 'POST', {
        idea: idea.trim(),
        genre,
      });
      setResult(data);
    } catch (e: any) {
      setError(e?.detail || e?.message || '生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-orange-50 via-white to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:py-12">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center justify-center gap-3">
            <Sparkles className="text-orange-500" size={32} />
            快速开始
          </h1>
          <p className="mt-3 text-gray-500 dark:text-gray-400">
            输入一句话灵感，AI 自动生成书名、大纲、细纲、第一章
          </p>
        </div>

        {/* Input */}
        <div className="card mb-8 p-6">
          <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">
            💡 写下一句话灵感
          </label>
          <textarea
            className="input mb-3 min-h-24 w-full rounded-lg border p-3 text-sm"
            placeholder="例如：修真界数学老师用微积分破阵、重生为小师妹的反派保镖、末世开店卖奶茶..."
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            disabled={loading}
          />

          <label className="mb-2 block text-sm font-semibold text-gray-700 dark:text-gray-300">
            📚 选择题材
          </label>
          <div className="flex flex-wrap gap-2 mb-4">
            {GENRES.map((g) => (
              <button
                key={g}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                  genre === g
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
                }`}
                onClick={() => setGenre(g)}
                disabled={loading}
              >
                {g}
              </button>
            ))}
          </div>

          <button
            className="btn-primary w-full"
            onClick={handleGenerate}
            disabled={loading || !idea.trim()}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <RefreshCw size={18} className="animate-spin" />
                生成中，约需 3-5 分钟...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <Zap size={18} />
                一键生成
              </span>
            )}
          </button>

          {error && (
            <p className="mt-3 text-sm text-red-500">{error}</p>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Titles */}
            <div className="card p-6">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
                <BookOpen size={20} className="text-orange-500" />
                可选书名
              </h2>
              <div className="flex flex-wrap gap-3">
                {(result.titles || []).map((t: string, i: number) => (
                  <span
                    key={i}
                    className={`rounded-full px-4 py-2 text-sm font-semibold ${
                      t === result.selected_title
                        ? 'bg-orange-500 text-white'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {/* Synopsis */}
            <div className="card p-6">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
                <FileText size={20} className="text-orange-500" />
                小说简介
              </h2>
              <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                {result.synopsis}
              </p>
            </div>

            {/* Outline */}
            <div className="card p-6">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
                📚 全书大纲（{result.outline?.length || 0}卷）
              </h2>
              {result.outline?.map((vol: any) => (
                <div key={vol.volume} className="mb-4 border-l-4 border-orange-300 pl-4">
                  <h3 className="font-semibold text-gray-800 dark:text-gray-200">
                    第{vol.volume}卷：{vol.title}
                  </h3>
                  <p className="text-xs text-gray-500">第{vol.start_chapter}-{vol.end_chapter}章 · {vol.theme}</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-gray-600 dark:text-gray-400">
                    {(vol.events || []).map((e: string, i: number) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {/* Detailed Outline */}
            <div className="card p-6">
              <h2 className="mb-3 text-lg font-semibold">📝 前三章细纲</h2>
              {result.detailed_outline?.map((ch: any) => (
                <div key={ch.chapter_num} className="mb-3 border-b border-gray-100 pb-3 dark:border-gray-700">
                  <h3 className="font-semibold text-gray-800 dark:text-gray-200">
                    第{ch.chapter_num}章：{ch.title}
                  </h3>
                  <p className="text-xs text-gray-500">场景：{ch.scene}</p>
                  <p className="text-xs text-gray-500">
                    情感：{ch.emotional_arc} · 伏笔：{ch.foreshadow_plant}
                  </p>
                  <p className="text-xs text-gray-500">结尾钩子：{ch.ending_hook}</p>
                </div>
              ))}
            </div>

            {/* First Chapter Preview */}
            <div className="card p-6">
              <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
                📖 第一章预览
              </h2>
              <p className="text-xs text-gray-500 mb-2">
                共 {result.first_chapter?.word_count} 字
              </p>
              <div className="max-h-64 overflow-y-auto rounded-lg bg-gray-50 p-4 text-sm leading-relaxed text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {result.first_chapter?.content}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                className="btn-primary flex-1"
                onClick={() => navigate(`/write/${result.project_id}`)}
              >
                <span className="flex items-center justify-center gap-2">
                  进入创作工作台
                  <ChevronRight size={18} />
                </span>
              </button>
              <button
                className="btn-secondary"
                onClick={() => {
                  setResult(null);
                  setIdea('');
                }}
              >
                重新开始
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
