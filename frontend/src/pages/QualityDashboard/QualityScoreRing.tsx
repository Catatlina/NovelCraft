import React from 'react';
import { motion } from 'framer-motion';

interface QualityScoreRingProps {
  score: number;
  maxScore?: number;
  size?: number;
}

/**
 * 综合质量分圆环组件
 * SVG 圆环，渐变填充路径 + 中心分数数字 + 动画过渡
 */
const QualityScoreRing: React.FC<QualityScoreRingProps> = ({
  score,
  maxScore = 100,
  size = 180,
}) => {
  const strokeWidth: number = 12;
  const radius: number = (size - strokeWidth) / 2;
  const circumference: number = 2 * Math.PI * radius;
  const progress: number = Math.min(score / maxScore, 1);
  const dashOffset: number = circumference * (1 - progress);

  // 根据分数确定颜色
  const getScoreColor = (): string => {
    if (score >= 80) return '#10B981';
    if (score >= 60) return '#FF6B35';
    if (score >= 40) return '#F59E0B';
    return '#FF2442';
  };

  const centerX: number = size / 2;
  const centerY: number = size / 2;

  return (
    <div className="relative inline-flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#FF6B35" />
            <stop offset="100%" stopColor="#FF2442" />
          </linearGradient>
        </defs>

        {/* 背景轨道 */}
        <circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth={strokeWidth}
          className="dark:stroke-gray-700"
        />

        {/* 进度弧线 */}
        <motion.circle
          cx={centerX}
          cy={centerY}
          r={radius}
          fill="none"
          stroke="url(#scoreGradient)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: dashOffset }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          transform={`rotate(-90 ${centerX} ${centerY})`}
        />
      </svg>

      {/* 中心分数 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-[36px] font-bold leading-none text-gray-800 dark:text-gray-100 font-mono"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          style={{ color: getScoreColor() }}
        >
          {score}
        </motion.span>
        <span className="mt-1 text-[11px] text-gray-400 dark:text-gray-500">
          综合质量分
        </span>
      </div>
    </div>
  );
};

export default QualityScoreRing;
