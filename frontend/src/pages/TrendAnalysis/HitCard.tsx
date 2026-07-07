import React from 'react';
import { Flame, BookOpen } from 'lucide-react';

interface HitCardProps {
  rank: number;
  title: string;
  author: string;
  genre: string;
  hotScore: number;
  platform?: string;
  coverGradient?: string;
  onClick?: () => void;
}

/** 类型色映射 */
const GENRE_COLORS: Record<string, string> = {
  玄幻: 'from-purple-600 to-indigo-700',
  都市: 'from-blue-600 to-cyan-700',
  言情: 'from-pink-500 to-rose-600',
  仙侠: 'from-teal-500 to-emerald-600',
  科幻: 'from-cyan-500 to-blue-600',
  悬疑: 'from-gray-600 to-slate-700',
  历史: 'from-amber-600 to-orange-700',
  游戏: 'from-green-500 to-teal-600',
  轻小说: 'from-violet-500 to-purple-600',
};

/** 排名徽章色 */
const RANK_COLORS: Record<number, string> = {
  1: 'bg-yellow-400 text-yellow-900',
  2: 'bg-gray-300 text-gray-700',
  3: 'bg-amber-600 text-amber-100',
};

/**
 * 爆款卡片组件
 * 渐变背景卡片，展示排名、爆款分、类型标签
 */
const HitCard: React.FC<HitCardProps> = ({
  rank,
  title,
  author,
  genre,
  hotScore,
  platform = '起点',
  onClick,
}) => {
  const gradientClass: string =
    GENRE_COLORS[genre] || 'from-primary-500 to-accent-500';
  const rankBadge: string =
    RANK_COLORS[rank] || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';

  return (
    <div
      onClick={onClick}
      className={`relative overflow-hidden rounded-xl bg-gradient-to-br ${gradientClass} p-4 text-white shadow-lg transition-all duration-200 hover:-translate-y-1 hover:shadow-xl cursor-pointer min-h-[160px]`}
    >
      {/* 排名徽章 */}
      <div className="absolute right-3 top-3">
        <span
          className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-[12px] font-bold ${rankBadge}`}
        >
          {rank}
        </span>
      </div>

      {/* 内容 */}
      <div className="flex flex-col gap-2 mt-4">
        <h4 className="text-[16px] font-bold leading-snug line-clamp-2">
          {title}
        </h4>
        <div className="flex items-center gap-2">
          <BookOpen size={12} className="opacity-70" />
          <span className="text-[12px] opacity-80">{author}</span>
        </div>

        {/* 底部：类型 + 热度 */}
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="inline-flex items-center rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] font-medium backdrop-blur-sm">
            {genre}
          </span>
          <span className="flex items-center gap-1 text-[13px] font-bold">
            <Flame size={14} />
            {hotScore}
          </span>
        </div>

        {/* 平台 */}
        <span className="text-[10px] opacity-50">{platform}</span>
      </div>
    </div>
  );
};

export default HitCard;
