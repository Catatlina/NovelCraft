import React from 'react';
import { motion } from 'framer-motion';
import { Star } from 'lucide-react';
import type { Chapter } from '@/types';

interface QualityBallProps {
  chapter?: Chapter;
}

/**
 * 右下角浮动质量评分球组件
 * Framer Motion 浮动动画，点击可查看质量详情
 */
const QualityBall: React.FC<QualityBallProps> = ({ chapter }) => {
  const score: number | null = chapter?.review_score ?? null;

  const handleClick = (): void => {
    // TODO: 打开质量详情面板或跳转到质量页面
    if (chapter) {
      // 可以触发质量评审或展示详情
    }
  };

  return (
    <motion.button
      onClick={handleClick}
      className="fixed bottom-6 right-6 z-40 flex h-16 w-16 cursor-pointer flex-col items-center justify-center rounded-full bg-gradient-primary font-mono text-white shadow-[0_2px_8px_rgba(255,107,53,0.25),0_10px_15px_rgba(0,0,0,0.06)] transition-transform hover:scale-105 lg:bottom-8 lg:right-8"
      aria-label={`当前章节质量分${score !== null ? `：${score}` : '：暂无'}`}
      animate={{
        y: [0, -6, 0],
      }}
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: 'easeInOut',
      }}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.95 }}
    >
      {score !== null ? (
        <>
          <span className="text-[20px] font-bold leading-none">{score}</span>
          <span className="mt-0.5 text-[9px] font-medium opacity-80">质量</span>
        </>
      ) : (
        <>
          <Star size={20} fill="currentColor" />
          <span className="mt-0.5 text-[9px] font-medium opacity-80">评分</span>
        </>
      )}
    </motion.button>
  );
};

export default QualityBall;
