/**
 * TranslatePage — 翻译流水线 UI
 * 路由: /translate/:projectId
 *
 * Phase 6.1: AI 翻译发布
 * 左侧：章节选择列表 + 平台选择 + 术语表
 * 右侧：原文/译文双栏对比预览
 */
import React, { useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Languages, Send, Plus, X, ChevronDown, Globe, BookOpen } from 'lucide-react';
import { useChapters } from '@/hooks/useApi';
import { api } from '@/api/client';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import type { ChapterSummary } from '@/types';

// ============================================================
// Constants
// ============================================================

// 与后端 prompts.py 的 PLATFORM_TRANSLATE_CONFIGS 保持一致——此前这里列了
// amazon_kdp/narou/munpia/dreame 四个后端根本不支持的平台(选了会400)，
// 却漏了后端真正支持的 wattpad/scribblehub。
const PLATFORMS: string[] = [
  'webnovel',
  'royalroad',
  'wattpad',
  'scribblehub',
];

const PLATFORM_LABELS: Record<string, string> = {
  webnovel: 'Webnovel (英文)',
  royalroad: 'Royal Road (英文)',
  wattpad: 'Wattpad (英文)',
  scribblehub: 'Scribble Hub (英文)',
};

// ============================================================
// Component
// ============================================================

const TranslatePage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: chapters, isLoading } = useChapters(projectId || '');

  // ---- 状态 ----
  const [selectedChapterIds, setSelectedChapterIds] = useState<Set<string>>(new Set());
  const [targetPlatform, setTargetPlatform] = useState<string>('webnovel');
  const [glossary, setGlossary] = useState<Array<{ source: string; target: string }>>([]);
  const [newSource, setNewSource] = useState<string>('');
  const [newTarget, setNewTarget] = useState<string>('');
  const [translating, setTranslating] = useState<boolean>(false);
  const [translatedText, setTranslatedText] = useState<string>('');
  const [sourceText, setSourceText] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const canTranslate: boolean =
    selectedChapterIds.size > 0 && targetPlatform !== '' && !translating;

  // ---- 事件 ----
  const toggleChapter = useCallback(
    (chapterId: string): void => {
      setSelectedChapterIds((prev: Set<string>) => {
        const next: Set<string> = new Set(prev);
        if (next.has(chapterId)) {
          next.delete(chapterId);
        } else {
          next.add(chapterId);
        }
        return next;
      });
    },
    [],
  );

  const selectAll = useCallback((): void => {
    if (!chapters) return;
    setSelectedChapterIds(new Set(chapters.map((c: ChapterSummary) => c.id)));
  }, [chapters]);

  const deselectAll = useCallback((): void => {
    setSelectedChapterIds(new Set());
  }, []);

  const addGlossaryEntry = useCallback((): void => {
    const s: string = newSource.trim();
    const t: string = newTarget.trim();
    if (!s || !t) return;
    setGlossary((prev) => [...prev, { source: s, target: t }]);
    setNewSource('');
    setNewTarget('');
  }, [newSource, newTarget]);

  const removeGlossaryEntry = useCallback((index: number): void => {
    setGlossary((prev) => prev.filter((_, i: number) => i !== index));
  }, []);

  /** 翻译章节 — 调用 POST /api/v1/translate/chapter/{chapter_id} */
  const handleTranslate = useCallback(async (): Promise<void> => {
    if (selectedChapterIds.size === 0) return;

    setTranslating(true);
    setError(null);
    setTranslatedText('');

    // 收集选中的章节原文用于预览
    const selected: ChapterSummary[] = (chapters || []).filter((ch: ChapterSummary) =>
      selectedChapterIds.has(ch.id),
    );
    // 列表接口(P0-1修复后)不再带正文，这里的预览只能先显示标题占位；
    // 真正提交翻译时后端会按 chapter_id 直接读取数据库里的正文，
    // 不依赖这段本地预览文本的准确性。
    const combinedSource: string = selected
      .map((ch: ChapterSummary) => `## ${ch.title}\n\n（正文将在提交时由服务器读取）`)
      .join('\n\n---\n\n');
    setSourceText(combinedSource);

    try {
      const glossaryObj: Record<string, string> = {};
      for (const entry of glossary) {
        glossaryObj[entry.source] = entry.target;
      }
      const glossaryParam: Record<string, string> | undefined =
        Object.keys(glossaryObj).length > 0 ? glossaryObj : undefined;

      // 此前这里只取第一章调用，且提交的字段名(platform/chapter_ids)后端
      // 根本不认识——platform被Pydantic静默忽略后永远用默认webnovel(用户
      // 选的平台不生效)，chapter_ids被忽略后选10章实际只翻1章。
      // 现改为: 字段名对齐后端(target_platform)，逐章顺序调用并拼接结果。
      const ids: string[] = [...selectedChapterIds];
      const pieces: string[] = [];
      for (let i = 0; i < ids.length; i++) {
        setTranslatedText(`正在翻译第 ${i + 1}/${ids.length} 章…\n\n${pieces.join('\n\n---\n\n')}`);
        const result = await api<{ translated_text: string }>(
          `/translate/chapter/${ids[i]}`,
          'POST',
          {
            target_platform: targetPlatform,
            glossary: glossaryParam,
          },
        );
        pieces.push(result.translated_text || '(本章翻译结果为空)');
      }
      setTranslatedText(pieces.join('\n\n---\n\n') || '翻译完成，结果为空');
    } catch (err: unknown) {
      const msg: string =
        err instanceof Error ? err.message : '翻译失败，请稍后重试';
      setError(msg);
    } finally {
      setTranslating(false);
    }
  }, [selectedChapterIds, targetPlatform, glossary, chapters]);

  // ---- 渲染 ----
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="lg" text="加载章节列表…" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <Languages size={28} className="text-primary-500" />
        <h1 className="text-display text-gray-800 dark:text-gray-100">翻译发布</h1>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* ===== 左侧：控制面板 ===== */}
        <div className="flex flex-col gap-4 lg:col-span-4">
          {/* 目标平台选择 */}
          <div className="card p-4">
            <label className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-gray-700 dark:text-gray-200">
              <Globe size={16} className="text-primary-500" />
              目标平台
            </label>
            <div className="relative">
              <select
                value={targetPlatform}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                  setTargetPlatform(e.target.value)
                }
                className="w-full appearance-none rounded-lg border border-gray-200 bg-white px-3 py-2.5 pr-8 text-[13px] text-gray-700 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400 dark:border-gray-600 dark:bg-dark-surface dark:text-gray-200"
              >
                {PLATFORMS.map((p: string) => (
                  <option key={p} value={p}>
                    {PLATFORM_LABELS[p]}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={16}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
              />
            </div>
          </div>

          {/* 术语表 */}
          <div className="card p-4">
            <label className="mb-2 flex items-center gap-2 text-[13px] font-semibold text-gray-700 dark:text-gray-200">
              <BookOpen size={16} className="text-primary-500" />
              术语表
            </label>
            <p className="mb-3 text-[11px] text-gray-400 dark:text-gray-500">
              设定专有名词的翻译映射，确保术语一致性
            </p>

            {/* 已有术语 */}
            {glossary.length > 0 && (
              <div className="mb-3 space-y-1.5">
                {glossary.map((entry, idx: number) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-1.5 text-[12px] dark:bg-gray-900/50"
                  >
                    <span>
                      <span className="font-mono text-gray-700 dark:text-gray-200">
                        {entry.source}
                      </span>
                      <span className="mx-1.5 text-gray-300 dark:text-gray-600">→</span>
                      <span className="font-mono text-primary-500">{entry.target}</span>
                    </span>
                    <button
                      onClick={() => removeGlossaryEntry(idx)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                      aria-label={`删除术语 ${entry.source}`}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* 新增术语 */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newSource}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setNewSource(e.target.value)
                }
                onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter') addGlossaryEntry();
                }}
                placeholder="原文"
                className="flex-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-[12px] text-gray-700 placeholder:text-gray-300 focus:border-primary-400 focus:outline-none dark:border-gray-600 dark:bg-dark-surface dark:text-gray-200"
              />
              <input
                type="text"
                value={newTarget}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setNewTarget(e.target.value)
                }
                onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter') addGlossaryEntry();
                }}
                placeholder="译文"
                className="flex-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-[12px] text-gray-700 placeholder:text-gray-300 focus:border-primary-400 focus:outline-none dark:border-gray-600 dark:bg-dark-surface dark:text-gray-200"
              />
              <button
                onClick={addGlossaryEntry}
                disabled={!newSource.trim() || !newTarget.trim()}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                aria-label="添加术语"
              >
                <Plus size={16} />
              </button>
            </div>
          </div>

          {/* 翻译触发 */}
          <button
            onClick={handleTranslate}
            disabled={!canTranslate}
            className="btn-primary flex items-center justify-center gap-2 py-2.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {translating ? (
              <>
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                翻译中…
              </>
            ) : (
              <>
                <Send size={16} />
                开始翻译 ({selectedChapterIds.size} 章)
              </>
            )}
          </button>

          {/* 错误提示 */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-[12px] text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}
        </div>

        {/* ===== 中间：章节列表 ===== */}
        <div className="card p-4 lg:col-span-3">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-[13px] font-semibold text-gray-700 dark:text-gray-200">
              选择章节
            </h3>
            <div className="flex gap-2">
              <button
                onClick={selectAll}
                className="text-[11px] text-primary-500 hover:text-primary-600 transition-colors"
              >
                全选
              </button>
              <button
                onClick={deselectAll}
                className="text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                取消
              </button>
            </div>
          </div>

          {!chapters || chapters.length === 0 ? (
            <p className="py-8 text-center text-[13px] text-gray-400">暂无章节</p>
          ) : (
            <div className="max-h-[500px] space-y-1 overflow-y-auto pr-1">
              {chapters.map((ch: ChapterSummary) => {
                const isSelected: boolean = selectedChapterIds.has(ch.id);
                return (
                  <label
                    key={ch.id}
                    className={`flex cursor-pointer items-center gap-2.5 rounded-md px-3 py-2 transition-colors ${
                      isSelected
                        ? 'bg-primary-50 dark:bg-primary-900/20'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-900/50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleChapter(ch.id)}
                      className="h-3.5 w-3.5 rounded border-gray-300 text-primary-500 focus:ring-primary-400"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[12px] font-medium text-gray-700 dark:text-gray-200">
                        {ch.title}
                      </p>
                      <p className="text-[11px] text-gray-400 dark:text-gray-500">
                        {ch.word_count != null ? `${ch.word_count.toLocaleString()} 字` : ''}
                        {ch.status ? ` · ${ch.status}` : ''}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>

        {/* ===== 右侧：双栏对比预览 ===== */}
        <div className="lg:col-span-5">
          {!sourceText && !translating ? (
            <div className="card flex h-full min-h-[300px] flex-col items-center justify-center p-8 text-center">
              <Languages size={48} className="mb-4 text-gray-200 dark:text-gray-700" />
              <p className="text-[13px] text-gray-400 dark:text-gray-500">
                选择章节并点击「开始翻译」，<br />
                将在此处显示原文与译文双栏对比
              </p>
            </div>
          ) : translating ? (
            <div className="card flex h-full min-h-[300px] items-center justify-center p-8">
              <LoadingSpinner size="lg" text="AI 翻译进行中…" />
            </div>
          ) : (
            <div className="card flex h-full flex-col overflow-hidden p-4">
              <h3 className="mb-3 text-[13px] font-semibold text-gray-700 dark:text-gray-200">
                翻译结果预览
              </h3>
              <div className="grid grid-cols-2 gap-3 overflow-hidden">
                {/* 原文 */}
                <div className="flex flex-col">
                  <span className="mb-1.5 text-[11px] font-semibold text-gray-400 uppercase tracking-wide">
                    原文
                  </span>
                  <div className="max-h-[500px] overflow-y-auto rounded-md border border-gray-200 bg-gray-50 p-3 dark:border-gray-600 dark:bg-gray-900/50">
                    <pre className="whitespace-pre-wrap font-sans text-[12px] leading-relaxed text-gray-700 dark:text-gray-300">
                      {sourceText}
                    </pre>
                  </div>
                </div>
                {/* 译文 */}
                <div className="flex flex-col">
                  <span className="mb-1.5 text-[11px] font-semibold text-primary-500 uppercase tracking-wide">
                    译文 ({PLATFORM_LABELS[targetPlatform]})
                  </span>
                  <div className="max-h-[500px] overflow-y-auto rounded-md border border-primary-200 bg-primary-50/30 p-3 dark:border-primary-800 dark:bg-primary-900/10">
                    <pre className="whitespace-pre-wrap font-sans text-[12px] leading-relaxed text-gray-700 dark:text-gray-300">
                      {translatedText}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TranslatePage;
