import React from 'react';
import { AlertTriangle, Sparkles } from 'lucide-react';
import type { DimensionScore } from '@/types';

interface DimensionCardsProps {
  dimensions: DimensionScore[];
  onRewrite?: (dimension: DimensionScore) => void;
  isRewriting?: boolean;
}

/** 维度颜色映射 */
const DIMENSION_COLORS: Record<string, string> = {
  readability: '#3B82F6',
  pacing: '#8B5CF6',
  logic: '#FF6B35',
  character: '#10B981',
  emotion: '#F59E0B',
  style: '#FF2442',
  foreshadow: '#6366F1',
};

/**
 * 7 维详情卡片组
 * 每张卡片展示维度名称、分数、进度条、问题列表
 * 低分维度（< 60 分）高亮红色边框 + "定向重写"按钮
 */
const DimensionCards: React.FC<DimensionCardsProps> = ({
  dimensions,
  onRewrite,
  isRewriting = false,
}) => {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {dimensions.map((dim) => {
        const isLow: boolean = dim.score < 60;
        const color: string = DIMENSION_COLORS[dim.name] || '#FF6B35';

        return (
          <div
            key={dim.name}
            className={`card flex flex-col gap-3 p-4 ${
              isLow
                ? 'border-red-300 shadow-[0_0_0_1px_rgba(239,68,68,0.15)] dark:border-red-700'
                : ''
            }`}
          >
            {/* 标题行 */}
            <div className="flex items-center justify-between">
              <h4 className="text-[14px] font-semibold text-gray-800 dark:text-gray-100">
                {dim.label}
              </h4>
              {isLow && (
                <AlertTriangle
                  size={16}
                  className="text-red-500 dark:text-red-400"
                />
              )}
            </div>

            {/* 分数 + 进度条 */}
            <div className="flex items-center gap-3">
              <span
                className="text-[24px] font-bold font-mono"
                style={{ color }}
              >
                {dim.score}
              </span>
              <div className="flex-1">
                <div className="progress">
                  <div
                    className="progress-bar"
                    style={{
                      width: `${dim.score}%`,
                      background: `linear-gradient(90deg, ${color}cc, ${color})`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* 问题列表 */}
            {dim.issues.length > 0 && (
              <ul className="space-y-1">
                {dim.issues.map((issue: string, idx: number) => (
                  <li
                    key={idx}
                    className="text-[12px] text-gray-500 dark:text-gray-400 leading-relaxed"
                  >
                    · {issue}
                  </li>
                ))}
              </ul>
            )}

            {/* 建议列表 */}
            {dim.suggestions.length > 0 && (
              <div className="mt-1 rounded-md bg-blue-50 p-2 dark:bg-blue-900/20">
                <p className="text-[11px] text-blue-600 dark:text-blue-400 leading-relaxed">
                  {dim.suggestions[0]}
                </p>
              </div>
            )}

            {/* 定向重写按钮（仅低分维度显示） */}
            {isLow && onRewrite && (
              <button
                onClick={() => onRewrite(dim)}
                disabled={isRewriting}
                className="btn-secondary btn-sm mt-auto gap-1.5 self-start"
              >
                <Sparkles size={13} />
                定向重写
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default DimensionCards;
