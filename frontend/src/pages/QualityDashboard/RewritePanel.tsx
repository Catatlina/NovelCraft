import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRight, Copy, Check } from 'lucide-react';
import type { DimensionScore, RewriteRequest } from '@/types';

interface RewritePanelProps {
  isOpen: boolean;
  onClose: () => void;
  originalText: string;
  rewrittenText: string;
  dimension: DimensionScore | null;
  chapterId: string;
  projectId: string;
  isLoading: boolean;
  onRewrite: (data: RewriteRequest) => void;
}

/**
 * AI 重写对比面板
 * 双栏展示重写前后的内容对比
 */
const RewritePanel: React.FC<RewritePanelProps> = ({
  isOpen,
  onClose,
  originalText,
  rewrittenText,
  dimension,
  chapterId,
  isLoading,
  onRewrite,
}) => {
  const [copied, setCopied] = React.useState<boolean>(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && panelRef.current) {
      panelRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [isOpen]);

  const handleCopy = (): void => {
    navigator.clipboard.writeText(rewrittenText || originalText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleRewriteClick = (): void => {
    if (!dimension || !chapterId) return;
    onRewrite({
      chapter_id: chapterId,
      dimension: dimension.name,
      target_segment: originalText,
      issue_description: dimension.issues.length > 0
        ? dimension.issues.join('；')
        : `重写以改善${dimension.label}维度`,
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          ref={panelRef}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ duration: 0.3 }}
          className="card overflow-hidden"
        >
          {/* 标题栏 */}
          <div className="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <span className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
                AI 重写对比
              </span>
              {dimension && (
                <span className="badge badge-primary text-[11px]">
                  {dimension.label} · {dimension.score}分
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {rewrittenText && (
                <button
                  onClick={handleCopy}
                  className="btn-ghost btn-sm gap-1"
                >
                  {copied ? (
                    <Check size={14} className="text-emerald-500" />
                  ) : (
                    <Copy size={14} />
                  )}
                  {copied ? '已复制' : '复制结果'}
                </button>
              )}
              <button onClick={onClose} className="btn-ghost btn-sm p-1">
                <X size={16} />
              </button>
            </div>
          </div>

          {/* 双栏对比 */}
          <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
            {/* 原始内容 */}
            <div>
              <h4 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                重写前
              </h4>
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50">
                <p className="text-[13px] leading-relaxed whitespace-pre-wrap text-gray-600 dark:text-gray-400 font-serif">
                  {originalText || '请先选择章节并触发质量评审'}
                </p>
              </div>
            </div>

            {/* 重写后 */}
            <div>
              <h4 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                重写后
              </h4>
              {isLoading ? (
                <div className="flex items-center justify-center rounded-lg border border-gray-200 bg-white p-8 dark:border-gray-700 dark:bg-dark-surface">
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
                    <span className="text-[12px] text-gray-400 dark:text-gray-500">
                      AI 正在重写…
                    </span>
                  </div>
                </div>
              ) : rewrittenText ? (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-900/20">
                  <p className="text-[13px] leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-200 font-serif">
                    {rewrittenText}
                  </p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-white p-8 dark:border-gray-600 dark:bg-dark-surface">
                  <ArrowRight
                    size={20}
                    className="mb-2 text-gray-300 dark:text-gray-600"
                  />
                  <p className="text-[12px] text-gray-400 dark:text-gray-500 mb-3">
                    点击按钮触发 AI 定向重写
                  </p>
                  <button
                    onClick={handleRewriteClick}
                    disabled={!dimension}
                    className="btn-primary btn-sm"
                  >
                    开始重写
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* 问题说明 */}
          {dimension && dimension.issues.length > 0 && (
            <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
              <h4 className="mb-1.5 text-[12px] font-semibold text-gray-500 dark:text-gray-400">
                检测到的问题
              </h4>
              <ul className="space-y-0.5">
                {dimension.issues.map((issue: string, idx: number) => (
                  <li
                    key={idx}
                    className="text-[13px] text-gray-600 dark:text-gray-300"
                  >
                    · {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default RewritePanel;
