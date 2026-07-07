import React from 'react';
import { Sparkles, TrendingUp, Star } from 'lucide-react';

interface TopicSuggestion {
  title: string;
  genre: string;
  score: number;
  tags: string[];
  reason: string;
}

interface TopicSuggestionsProps {
  suggestions: TopicSuggestion[];
  isLoading: boolean;
}

/**
 * AI 选题建议组件
 * 3 条选题推荐卡片，含标题/类型/评分/简介
 */
const TopicSuggestions: React.FC<TopicSuggestionsProps> = ({
  suggestions,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={18} className="text-primary-500" />
          <h3 className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            AI 选题建议
          </h3>
        </div>
        <div className="flex items-center justify-center py-10">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
        </div>
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={18} className="text-primary-500" />
          <h3 className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            AI 选题建议
          </h3>
        </div>
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <p className="text-[13px] text-gray-400 dark:text-gray-500">
            完成市场分析后，AI 将为你生成选题建议
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="mb-4 flex items-center gap-2">
        <Sparkles size={18} className="text-primary-500" />
        <h3 className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          AI 选题建议
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {suggestions.map((item: TopicSuggestion, idx: number) => (
          <div
            key={idx}
            className="flex flex-col rounded-xl border border-gray-200 p-4 transition-all duration-200 hover:border-primary-300 hover:shadow-sm dark:border-gray-700 dark:hover:border-primary-700"
          >
            {/* 排名 + 评分 */}
            <div className="mb-3 flex items-center justify-between">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-[11px] font-bold text-primary-700 dark:bg-primary-900/40 dark:text-primary-400">
                {idx + 1}
              </span>
              <span className="flex items-center gap-1 text-[13px] font-bold text-primary-500">
                <Star size={13} fill="currentColor" />
                {item.score}
              </span>
            </div>

            {/* 标题 */}
            <h4 className="mb-2 text-[14px] font-semibold text-gray-800 dark:text-gray-100">
              {item.title}
            </h4>

            {/* 类型标签 */}
            <div className="mb-2 flex flex-wrap gap-1">
              <span className="badge badge-primary text-[10px]">{item.genre}</span>
              {item.tags.map((tag: string) => (
                <span
                  key={tag}
                  className="badge bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 text-[10px]"
                >
                  {tag}
                </span>
              ))}
            </div>

            {/* 推荐理由 */}
            <div className="mt-auto flex items-start gap-1.5 rounded-md bg-amber-50 p-2 dark:bg-amber-900/20">
              <TrendingUp size={12} className="mt-0.5 shrink-0 text-amber-500" />
              <p className="text-[11px] text-amber-700 dark:text-amber-400 leading-relaxed">
                {item.reason}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TopicSuggestions;
