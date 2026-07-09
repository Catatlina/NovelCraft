import React from 'react';
import { ChevronRight, ExternalLink } from 'lucide-react';
import type { ChapterSummary } from '@/types';
import { fmtWords } from '@/utils/helpers';

interface ChapterQualityRow {
  chapter: ChapterSummary;
  scores: Record<string, number> | null;
  overallScore: number | null;
}

interface ChapterQualityTableProps {
  rows: ChapterQualityRow[];
  selectedChapterId?: string;
  onSelectChapter?: (chapterId: string) => void;
  isLoading?: boolean;
}

/** 表头定义 */
const COLUMNS: { key: string; label: string; width: string }[] = [
  { key: 'chapter', label: '章节', width: 'min-w-[140px]' },
  { key: 'words', label: '字数', width: 'min-w-[80px]' },
  { key: 'readability', label: '可读性', width: 'min-w-[72px]' },
  { key: 'pacing', label: '节奏', width: 'min-w-[64px]' },
  { key: 'logic', label: '逻辑', width: 'min-w-[64px]' },
  { key: 'character', label: '人物', width: 'min-w-[64px]' },
  { key: 'emotion', label: '情感', width: 'min-w-[64px]' },
  { key: 'style', label: '文笔', width: 'min-w-[64px]' },
  { key: 'foreshadow', label: '伏笔', width: 'min-w-[64px]' },
  { key: 'overall', label: '综合', width: 'min-w-[72px]' },
];

/**
 * 章节质量评分表
 * 展示最近章节 × 7 维评分的表格
 */
const ChapterQualityTable: React.FC<ChapterQualityTableProps> = ({
  rows,
  selectedChapterId,
  onSelectChapter,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="card p-0 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            章节质量列表
          </h3>
        </div>
        <div className="flex items-center justify-center py-16">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
        </div>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="card p-0 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            章节质量列表
          </h3>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-[13px] text-gray-400 dark:text-gray-500">
            暂无章节质量数据
          </p>
        </div>
      </div>
    );
  }

  /** 根据分数返回颜色类 */
  const scoreColor = (s: number): string => {
    if (s >= 80) return 'text-emerald-500 dark:text-emerald-400';
    if (s >= 60) return 'text-primary-500 dark:text-primary-400';
    if (s >= 40) return 'text-amber-500 dark:text-amber-400';
    return 'text-red-500 dark:text-red-400';
  };

  return (
    <div className="card p-0 overflow-hidden">
      {/* 表头 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          章节质量列表
        </h3>
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-700">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`${col.width} px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isSelected: boolean = row.chapter.id === selectedChapterId;
              return (
                <tr
                  key={row.chapter.id}
                  onClick={() => onSelectChapter?.(row.chapter.id)}
                  className={`border-b border-gray-50 transition-colors duration-150 dark:border-gray-800 ${
                    isSelected
                      ? 'bg-primary-50/50 dark:bg-primary-900/10'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
                  } ${onSelectChapter ? 'cursor-pointer' : ''}`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {isSelected && (
                        <ChevronRight size={14} className="text-primary-500" />
                      )}
                      <span className="text-[13px] font-medium text-gray-700 dark:text-gray-200">
                        Ch.{row.chapter.chapter_num} {row.chapter.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[12px] text-gray-400 dark:text-gray-500 font-mono">
                      {fmtWords(row.chapter.word_count)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.readability ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.readability ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.pacing ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.pacing ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.logic ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.logic ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.character ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.character ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.emotion ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.emotion ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.style ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.style ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[13px] font-mono font-semibold ${row.scores ? scoreColor(row.scores.foreshadow ?? 0) : 'text-gray-300 dark:text-gray-600'}`}
                    >
                      {row.scores?.foreshadow ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[14px] font-bold font-mono ${row.overallScore != null ? scoreColor(row.overallScore) : 'text-gray-300 dark:text-gray-600'}`}
                      >
                        {row.overallScore ?? '未审查'}
                      </span>
                      {onSelectChapter && (
                        <ExternalLink size={12} className="text-gray-300 dark:text-gray-600" />
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ChapterQualityTable;
