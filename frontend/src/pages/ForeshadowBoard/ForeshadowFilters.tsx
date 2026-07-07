import React, { useState, useCallback, useRef } from 'react';
import { Search, Zap } from 'lucide-react';
import type { ForeshadowStatus } from '@/types';

interface ForeshadowFiltersProps {
  statusFilter: ForeshadowStatus | 'all';
  searchTerm: string;
  onStatusChange: (status: ForeshadowStatus | 'all') => void;
  onSearchChange: (term: string) => void;
  onCheckOverdue: () => void;
  isCheckingOverdue: boolean;
}

const STATUS_OPTIONS: { value: ForeshadowStatus | 'all'; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'planted', label: '已埋设' },
  { value: 'paid_off', label: '已回收' },
  { value: 'overdue', label: '超期' },
];

/**
 * 伏笔筛选栏组件
 * 状态下拉选择器 + 搜索输入框（300ms 防抖） + 检测超期按钮
 */
const ForeshadowFilters: React.FC<ForeshadowFiltersProps> = ({
  statusFilter,
  searchTerm,
  onStatusChange,
  onSearchChange,
  onCheckOverdue,
  isCheckingOverdue,
}) => {
  const [localSearch, setLocalSearch] = useState<string>(searchTerm);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value: string = e.target.value;
      setLocalSearch(value);

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(() => {
        onSearchChange(value);
      }, 300);
    },
    [onSearchChange],
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* 状态下拉选择器 */}
      <div className="flex items-center rounded-lg border border-gray-200 bg-white p-0.5 dark:border-gray-700 dark:bg-dark-surface">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onStatusChange(opt.value)}
            className={`rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors duration-150 ${
              statusFilter === opt.value
                ? 'bg-primary-500 text-white shadow-sm'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* 搜索输入框 */}
      <div className="relative flex-1 min-w-[200px] max-w-[320px]">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500"
        />
        <input
          type="text"
          value={localSearch}
          onChange={handleSearchChange}
          placeholder="搜索伏笔内容…"
          className="input pl-9"
        />
      </div>

      {/* 检测超期按钮 */}
      <button
        onClick={onCheckOverdue}
        disabled={isCheckingOverdue}
        className="btn-secondary gap-1.5"
      >
        <Zap size={14} className={isCheckingOverdue ? 'animate-pulse' : ''} />
        {isCheckingOverdue ? '检测中…' : '检测超期'}
      </button>
    </div>
  );
};

export default ForeshadowFilters;
