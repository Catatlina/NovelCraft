import React from 'react';
import ForeshadowCard from '@/components/shared/ForeshadowCard';
import type { Foreshadow } from '@/types';

interface ForeshadowColumnProps {
  title: string;
  count: number;
  foreshadows: Foreshadow[];
  color: 'orange' | 'green' | 'red';
  icon: React.ReactNode;
  onMarkPayoff?: (foreshadowId: string) => void;
  onCheckPayoff?: (foreshadowId: string) => void;
}

const COLOR_CLASSES: Record<string, { header: string; badge: string; border: string }> = {
  orange: {
    header: 'border-t-orange-400 bg-orange-50/50 dark:border-t-orange-500 dark:bg-orange-900/10',
    badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400',
    border: 'border-orange-200 dark:border-orange-800',
  },
  green: {
    header: 'border-t-emerald-400 bg-emerald-50/50 dark:border-t-emerald-500 dark:bg-emerald-900/10',
    badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
    border: 'border-emerald-200 dark:border-emerald-800',
  },
  red: {
    header: 'border-t-red-400 bg-red-50/50 dark:border-t-red-500 dark:bg-red-900/10',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
    border: 'border-red-200 dark:border-red-800',
  },
};

/**
 * 伏笔看板单列组件
 * 展示某一状态（未回收/已回收/超期）的伏笔卡片列表
 */
const ForeshadowColumn: React.FC<ForeshadowColumnProps> = ({
  title,
  count,
  foreshadows,
  color,
  icon,
  onMarkPayoff,
  onCheckPayoff,
}) => {
  const cls = COLOR_CLASSES[color];

  return (
    <div
      className={`flex flex-col rounded-xl border ${cls.border} overflow-hidden`}
    >
      {/* 列标题 */}
      <div
        className={`flex items-center gap-2 border-t-[3px] px-4 py-3 ${cls.header}`}
      >
        <span className="flex items-center gap-1.5 text-[14px] font-semibold text-gray-700 dark:text-gray-200">
          {icon}
          {title}
        </span>
        <span
          className={`ml-auto inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[11px] font-bold ${cls.badge}`}
        >
          {count}
        </span>
      </div>

      {/* 卡片列表 */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2 scrollbar-thin max-h-[calc(100vh-360px)]">
        {foreshadows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-[13px] text-gray-400 dark:text-gray-500">
              暂无{title}的伏笔
            </p>
          </div>
        ) : (
          foreshadows.map((f) => (
            <ForeshadowCard
              key={f.id}
              foreshadow={f}
              onMarkPayoff={onMarkPayoff}
              onCheckPayoff={onCheckPayoff}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default ForeshadowColumn;
