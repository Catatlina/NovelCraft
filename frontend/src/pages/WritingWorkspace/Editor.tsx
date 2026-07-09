import React, { useState, useCallback } from 'react';
import { ArrowLeft, Eye, EyeOff } from 'lucide-react';
import AIToolbar from '@/components/shared/AIToolbar';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import { STATE_LABELS, fmtWords } from '@/utils/helpers';
import { useGenerateChapter, useQualityReview, useQualityRewrite, useDeslop } from '@/hooks/useApi';
import type { Project, Chapter } from '@/types';

interface EditorProps {
  project: Project;
  chapter?: Chapter;
  chaptersLoading: boolean;
  onBack: () => void;
}

/**
 * 中央编辑器组件
 * 显示章节内容、顶部信息栏、底部 AI 工具栏
 */
const Editor: React.FC<EditorProps> = ({
  project,
  chapter,
  chaptersLoading,
  onBack,
}) => {
  const [isReadOnly, setIsReadOnly] = useState<boolean>(true);
  const [editContent, setEditContent] = useState<string>('');

  // API hooks
  const genMutation = useGenerateChapter(project.id);
  const reviewMutation = useQualityReview();
  const rewriteMutation = useQualityRewrite();
  const deslopMutation = useDeslop();

  // 同步编辑内容
  React.useEffect(() => {
    if (chapter) {
      setEditContent(chapter.content || '');
    }
  }, [chapter?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleReadOnly = useCallback(() => {
    setIsReadOnly((prev: boolean) => !prev);
  }, []);

  // AI 工具栏回调 — 连接实际 API
  const handleContinue = useCallback(() => {
    if (!chapter) return;
    genMutation.mutate({ mode: 'continue' });
  }, [chapter, genMutation]);

  const handleRewrite = useCallback(() => {
    if (!chapter) return;
    rewriteMutation.mutate({
      chapter_id: chapter.id,
      dimension: 'rewrite',
      target_segment: chapter.content || '',
      issue_description: '整体优化表达',
    });
  }, [chapter, rewriteMutation]);

  const handleDeslop = useCallback(() => {
    if (!chapter) return;
    deslopMutation.mutate({ content: chapter.content || '' });
  }, [chapter, deslopMutation]);

  const handleReview = useCallback(() => {
    if (!chapter) return;
    reviewMutation.mutate({
      chapter_id: chapter.id,
      chapter_content: chapter.content || '',
      outline: '',
      context: '',
    });
  }, [chapter, reviewMutation]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-white dark:bg-dark-surface">
      {/* 顶部信息栏 */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-gray-100 px-4 dark:border-gray-700">
        <div className="flex items-center gap-3 min-w-0">
          {/* PC 端返回按钮 */}
          <button
            onClick={onBack}
            className="hidden rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 lg:block"
            aria-label="返回"
          >
            <ArrowLeft size={16} />
          </button>

          {chapter ? (
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-[12px] text-gray-400 dark:text-gray-500 truncate">
                {chapter.volume ? `${chapter.volume} · ` : ''}
              </span>
              <span className="text-[12px] text-gray-300 dark:text-gray-600">/</span>
              <span className="truncate text-[13px] font-semibold text-gray-700 dark:text-gray-200">
                第{chapter.chapter_num}章 {chapter.title || ''}
              </span>
            </div>
          ) : (
            <span className="text-[13px] text-gray-400 dark:text-gray-500">
              {chaptersLoading ? '加载章节...' : '请选择一个章节'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          {chapter && (
            <>
              <span className="font-mono text-[12px] text-gray-400 dark:text-gray-500">
                {fmtWords(chapter.word_count || 0)}字
              </span>
              <span
                className={`badge ${
                  chapter.status === 'completed'
                    ? 'badge-success'
                    : chapter.status === 'reviewed'
                      ? 'badge-info'
                      : chapter.status === 'in_progress'
                        ? 'badge-warning'
                        : 'badge-primary'
                }`}
              >
                {chapter.status === 'completed'
                  ? '已完成'
                  : chapter.status === 'reviewed'
                    ? '已审核'
                    : chapter.status === 'in_progress'
                      ? '写作中'
                      : '草稿'}
              </span>
            </>
          )}
          <div className="h-4 w-px bg-gray-200 dark:bg-gray-600" />
          <button
            onClick={toggleReadOnly}
            className="btn-ghost !h-7 !px-2 text-[12px]"
            title={isReadOnly ? '切换到编辑模式' : '切换到只读模式'}
          >
            {isReadOnly ? <Eye size={14} /> : <EyeOff size={14} />}
            <span className="hidden sm:inline">{isReadOnly ? '只读' : '编辑'}</span>
          </button>
        </div>
      </div>

      {/* 编辑器正文区 */}
      <div className="flex-1 overflow-y-auto">
        {chaptersLoading ? (
          <div className="flex h-full items-center justify-center">
            <LoadingSpinner text="加载章节内容..." />
          </div>
        ) : chapter ? (
          <div className="mx-auto max-w-[720px] px-6 py-8">
            {/* 章节标题 */}
            <h1 className="mb-8 text-center font-serif text-[24px] font-bold leading-relaxed text-gray-800 dark:text-gray-100">
              第{chapter.chapter_num}章 {chapter.title || ''}
            </h1>

            {/* 正文 */}
            {isReadOnly ? (
              <article className="font-serif text-[16px] leading-[1.8] text-gray-700 dark:text-gray-300">
                {chapter.content ? (
                  chapter.content.split('\n').map((paragraph: string, idx: number) => (
                    <p key={idx} className="mb-4 indent-8">
                      {paragraph}
                    </p>
                  ))
                ) : (
                  <p className="text-center text-gray-400 dark:text-gray-500">
                    暂无内容，请先生成本章节
                  </p>
                )}
              </article>
            ) : (
              <textarea
                className="min-h-[400px] w-full resize-y rounded-lg border border-gray-200 bg-transparent p-4 font-serif text-[16px] leading-[1.8] text-gray-700 outline-none transition-colors focus:border-primary-300 focus:ring-2 focus:ring-primary-500/10 dark:border-gray-600 dark:text-gray-300 dark:focus:border-primary-600"
                value={editContent}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setEditContent(e.target.value)
                }
                placeholder="在此编辑章节内容..."
              />
            )}

            {/* 字数统计 */}
            <div className="mt-8 border-t border-gray-100 pt-4 text-center dark:border-gray-700">
              <span className="font-mono text-[12px] text-gray-400 dark:text-gray-500">
                — {fmtWords(chapter.word_count || 0)} 字 —
              </span>
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-gray-400 dark:text-gray-500">
            <span className="text-5xl">📖</span>
            <p className="text-sm">选择左侧章节开始阅读或编辑</p>
            <p className="text-[12px]">
              《{project.title}》· {STATE_LABELS[project.current_state]}
            </p>
          </div>
        )}
      </div>

      {/* 底部 AI 工具栏 */}
      {chapter && (
        <AIToolbar
          onContinue={handleContinue}
          onRewrite={handleRewrite}
          onDeslop={handleDeslop}
          onReview={handleReview}
        />
      )}
    </div>
  );
};

export default Editor;
