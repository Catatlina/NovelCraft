import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, FileText, Rocket, Target, Users } from 'lucide-react';

interface MarketPredictionData {
  overallScore: number;
  titleFit: number;
  openingHook: number;
  marketFit: number;
  differentiation: number;
  suggestions: string[];
}

interface MarketPredictionProps {
  data: MarketPredictionData | null;
  isLoading: boolean;
}

/**
 * 市场热度预测组件
 * 总分 + 4 项分项评分 + 进度条 + 建议列表
 */
const MarketPrediction: React.FC<MarketPredictionProps> = ({ data, isLoading }) => {
  if (isLoading) {
    return (
      <div className="card">
        <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          市场热度预测
        </h3>
        <div className="flex items-center justify-center py-10">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card">
        <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          市场热度预测
        </h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Target size={28} className="mb-2 text-gray-300 dark:text-gray-600" />
          <p className="text-[13px] text-gray-400 dark:text-gray-500">
            请先填写分析表单，提交后查看市场热度预测
          </p>
        </div>
      </div>
    );
  }

  const items: { icon: React.ReactNode; label: string; score: number; key: string }[] = [
    { icon: <FileText size={16} />, label: '标题吸引力', score: data.titleFit, key: 'titleFit' },
    { icon: <Rocket size={16} />, label: '开头Hook', score: data.openingHook, key: 'openingHook' },
    { icon: <Target size={16} />, label: '市场契合度', score: data.marketFit, key: 'marketFit' },
    { icon: <Users size={16} />, label: '差异化竞争', score: data.differentiation, key: 'differentiation' },
  ];

  /** 分数颜色 */
  const barColor = (s: number): string => {
    if (s >= 80) return 'bg-emerald-500';
    if (s >= 60) return 'bg-primary-500';
    if (s >= 40) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="card">
      <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
        市场热度预测
      </h3>

      {/* 总分 */}
      <div className="mb-6 flex items-center gap-4">
        <motion.div
          className="flex h-[80px] w-[80px] items-center justify-center rounded-2xl bg-gradient-primary shadow-primary"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex flex-col items-center">
            <span className="text-[28px] font-bold text-white font-mono leading-none">
              {data.overallScore}
            </span>
            <span className="text-[10px] text-white/70">综合分</span>
          </div>
        </motion.div>
        <div>
          <p className="text-[14px] font-semibold text-gray-800 dark:text-gray-100">
            市场潜力综合评估
          </p>
          <p className="text-[12px] text-gray-500 dark:text-gray-400">
            基于标题、开头、市场、差异化的多维度分析
          </p>
        </div>
      </div>

      {/* 4 项分项 */}
      <div className="space-y-3 mb-6">
        {items.map((item) => (
          <div key={item.key} className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              {item.icon}
            </span>
            <div className="flex-1">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-[13px] font-medium text-gray-700 dark:text-gray-200">
                  {item.label}
                </span>
                <span className="text-[13px] font-bold font-mono text-gray-800 dark:text-gray-100">
                  {item.score}
                </span>
              </div>
              <div className="progress">
                <div
                  className={`progress-bar ${barColor(item.score)}`}
                  style={{ width: `${item.score}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 建议列表 */}
      {data.suggestions.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/50">
          <div className="mb-2 flex items-center gap-1.5">
            <TrendingUp size={14} className="text-primary-500" />
            <span className="text-[12px] font-semibold text-gray-600 dark:text-gray-300">
              AI 优化建议
            </span>
          </div>
          <ul className="space-y-1">
            {data.suggestions.map((s: string, idx: number) => (
              <li
                key={idx}
                className="text-[13px] text-gray-600 dark:text-gray-400 leading-relaxed"
              >
                {idx + 1}. {s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default MarketPrediction;
