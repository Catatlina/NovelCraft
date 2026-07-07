import React from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KPICardProps {
  icon: React.ReactNode;
  label: string;
  /** 数值，支持动画数字 */
  value: number;
  /** 数值单位，如 "字"、"章"、"%" */
  unit?: string;
  /** 趋势方向 */
  trend?: 'up' | 'down' | 'neutral';
  /** 趋势描述文本，如 "+12% 较上周" */
  trendLabel?: string;
}

/**
 * KPI 卡片组件
 * 展示关键指标，支持 Framer Motion useSpring 数字滚动动画
 */
const KPICard: React.FC<KPICardProps> = ({
  icon,
  label,
  value,
  unit,
  trend,
  trendLabel,
}) => {
  const springValue = useSpring(0, { stiffness: 80, damping: 20 });
  const displayValue = useTransform(springValue, (v: number) =>
    Math.round(v).toLocaleString(),
  );

  React.useEffect(() => {
    springValue.set(value);
  }, [value, springValue]);

  return (
    <div className="card flex flex-col gap-3 p-5">
      {/* 顶部：图标 + 标签 */}
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-50 text-primary-500 dark:bg-primary-900/30 dark:text-primary-400">
          {icon}
        </span>
        <span className="text-[13px] font-medium text-gray-500 dark:text-gray-400">
          {label}
        </span>
      </div>

      {/* 数值 */}
      <div className="flex items-baseline gap-1">
        <motion.span className="text-mono text-[20px] font-semibold text-gray-800 dark:text-gray-100">
          {displayValue}
        </motion.span>
        {unit && (
          <span className="text-[13px] text-gray-400 dark:text-gray-500">
            {unit}
          </span>
        )}
      </div>

      {/* 趋势 */}
      {trend && (
        <div className="flex items-center gap-1">
          {trend === 'up' ? (
            <TrendingUp size={14} className="text-emerald-500" />
          ) : trend === 'down' ? (
            <TrendingDown size={14} className="text-red-500" />
          ) : null}
          {trendLabel && (
            <span
              className={`text-[12px] font-mono font-medium ${
                trend === 'up'
                  ? 'text-emerald-500'
                  : trend === 'down'
                    ? 'text-red-500'
                    : 'text-gray-400'
              }`}
            >
              {trendLabel}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default KPICard;
