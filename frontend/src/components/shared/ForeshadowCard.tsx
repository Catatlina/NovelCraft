import React from 'react';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import type { Foreshadow, ForeshadowStatus } from '@/types';

interface ForeshadowCardProps {
  foreshadow: Foreshadow;
  onMarkPayoff?: (foreshadowId: string) => void;
  onCheckPayoff?: (foreshadowId: string) => void;
}

/** 状态配置 */
const STATUS_CONFIG: Record<
  ForeshadowStatus,
  { icon: React.ReactNode; label: string; colorClass: string; borderClass: string }
> = {
  planted: {
    icon: <Clock size={14} />,
    label: '已埋设',
    colorClass: 'text-gray-500 dark:text-gray-400',
    borderClass: 'border-l-gray-400',
  },
  paid_off: {
    icon: <CheckCircle2 size={14} />,
    label: '已回收',
    colorClass: 'text-emerald-500 dark:text-emerald-400',
    borderClass: 'border-l-emerald-500',
  },
  overdue: {
    icon: <AlertCircle size={14} />,
    label: '已逾期',
    colorClass: 'text-red-500 dark:text-red-400',
    borderClass: 'border-l-red-500',
  },
};

/**
 * 伏笔卡片组件
 * 展示单条伏笔的摘要信息与状态徽章
 */
const ForeshadowCard: React.FC<ForeshadowCardProps> = ({
  foreshadow,
  onMarkPayoff,
  onCheckPayoff,
}) => {
  const cfg = STATUS_CONFIG[foreshadow.status];
  const isOverdue: boolean = foreshadow.status === 'overdue';
  const isPlanted: boolean = foreshadow.status === 'planted';

  return (
    <div
      className={`rounded-md border border-gray-200 bg-white p-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all duration-150 hover:shadow-sm dark:border-gray-700 dark:bg-dark-surface border-l-[3px] ${cfg.borderClass}`}
    >
      {/* 头部：状态徽章 + 操作按钮 */}
      <div className="mb-2 flex items-center justify-between">
        <span
          className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium ${cfg.colorClass} bg-opacity-10 ${
            foreshadow.status === 'planted'
              ? 'bg-gray-100 dark:bg-gray-800'
              : foreshadow.status === 'paid_off'
                ? 'bg-emerald-50 dark:bg-emerald-900/30'
                : 'bg-red-50 dark:bg-red-900/30'
          }`}
        >
          {cfg.icon}
          {cfg.label}
        </span>

        <div className="flex gap-1">
          {isPlanted && onMarkPayoff && (
            <button
              onClick={() => onMarkPayoff(foreshadow.id)}
              className="rounded px-2 py-0.5 text-[11px] text-primary-500 transition-colors hover:bg-primary-50 dark:hover:bg-primary-900/30"
            >
              标记回收
            </button>
          )}
          {(isPlanted || isOverdue) && onCheckPayoff && (
            <button
              onClick={() => onCheckPayoff(foreshadow.id)}
              className="rounded px-2 py-0.5 text-[11px] text-blue-500 transition-colors hover:bg-blue-50 dark:hover:bg-blue-900/30"
            >
              AI 检查
            </button>
          )}
        </div>
      </div>

      {/* 内容 */}
      <p className="text-[13px] leading-relaxed text-gray-700 dark:text-gray-200 line-clamp-3">
        {foreshadow.content}
      </p>

      {/* 底部元信息 */}
      <div className="mt-2 flex items-center gap-4 text-[11px] text-gray-400 dark:text-gray-500">
        <span>
          埋于第{foreshadow.planted_chapter}章
        </span>
        {foreshadow.target_chapter && (
          <span>
            目标第{foreshadow.target_chapter}章
          </span>
        )}
        {foreshadow.resolved_chapter && (
          <span className="text-emerald-500 dark:text-emerald-400">
            回收于第{foreshadow.resolved_chapter}章
          </span>
        )}
      </div>
    </div>
  );
};

export default ForeshadowCard;
