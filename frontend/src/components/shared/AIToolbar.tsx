import React from 'react';
import { Pencil, Sparkles, Scissors, Search, Languages } from 'lucide-react';

interface AIToolbarProps {
  /** 续写 */
  onContinue?: () => void;
  /** AI 改写 */
  onRewrite?: () => void;
  /** 去口语化 */
  onDeslop?: () => void;
  /** 质量评审 */
  onReview?: () => void;
  /** 翻译 */
  onTranslate?: () => void;
  /** 禁用所有按钮 */
  disabled?: boolean;
}

/**
 * AI 工具栏组件
 * 固定在编辑器底部的 5 个 AI 功能按钮
 */
const AIToolbar: React.FC<AIToolbarProps> = ({
  onContinue,
  onRewrite,
  onDeslop,
  onReview,
  onTranslate,
  disabled = false,
}) => {
  const buttons: {
    key: string;
    label: string;
    icon: React.ReactNode;
    action?: () => void;
  }[] = [
    { key: 'continue', label: '续写', icon: <Pencil size={18} />, action: onContinue },
    { key: 'rewrite', label: '改写', icon: <Sparkles size={18} />, action: onRewrite },
    { key: 'deslop', label: '去口语', icon: <Scissors size={18} />, action: onDeslop },
    { key: 'review', label: '评审', icon: <Search size={18} />, action: onReview },
    { key: 'translate', label: '翻译', icon: <Languages size={18} />, action: onTranslate },
  ];

  return (
    <div className="flex items-center justify-center gap-2 border-t border-gray-200 bg-white px-6 py-3 dark:border-gray-700 dark:bg-dark-surface">
      {buttons.map((btn) => (
        <button
          key={btn.key}
          onClick={btn.action}
          disabled={disabled || !btn.action}
          className="flex flex-col items-center gap-0.5 rounded-md border border-gray-200 bg-transparent px-3 py-2 text-[11px] font-medium text-gray-500 transition-all duration-150 hover:border-primary-300 hover:text-primary-500 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:text-gray-400 dark:hover:border-primary-700 dark:hover:text-primary-400"
        >
          <span className="flex h-5 w-5 items-center justify-center">{btn.icon}</span>
          <span>{btn.label}</span>
        </button>
      ))}
    </div>
  );
};

export default AIToolbar;
