import React, { useState, useCallback, useMemo } from 'react';
import { TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import HitCard from './HitCard';
import AnalysisForm from './AnalysisForm';
import MarketPrediction from './MarketPrediction';
import GenreTrends from './GenreTrends';
import TopicSuggestions from './TopicSuggestions';
import { useQualityBenchmarks } from '@/hooks/useApi';
import type { HitAnalysisRequest, HitBenchmark } from '@/types';

/** 模拟爆款数据 */
const MOCK_HITS: HitBenchmark[] = [
  {
    id: 'h1',
    title: '星辰变',
    author: '我吃西红柿',
    platform: '起点中文网',
    hot_score: 98,
    read_count: 52000000,
    tags: ['玄幻', '热血', '升级流'],
    similarity: 0.85,
    highlights: ['世界观宏大', '升级体系清晰'],
  },
  {
    id: 'h2',
    title: '大奉打更人',
    author: '卖报小郎君',
    platform: '起点中文网',
    hot_score: 96,
    read_count: 48000000,
    tags: ['仙侠', '穿越', '搞笑'],
    similarity: 0.78,
    highlights: ['设定新颖', '笑点密集'],
  },
  {
    id: 'h3',
    title: '诡秘之主',
    author: '爱潜水的乌贼',
    platform: '起点中文网',
    hot_score: 95,
    read_count: 45000000,
    tags: ['奇幻', '克苏鲁', '蒸汽朋克'],
    similarity: 0.72,
    highlights: ['设定独特', '悬念铺设出色'],
  },
  {
    id: 'h4',
    title: '我在精神病院学斩神',
    author: '三九音域',
    platform: '番茄小说',
    hot_score: 93,
    read_count: 41000000,
    tags: ['都市', '异能', '热血'],
    similarity: 0.80,
    highlights: ['节奏快', '爽点密集'],
  },
  {
    id: 'h5',
    title: '遮天',
    author: '辰东',
    platform: '起点中文网',
    hot_score: 91,
    read_count: 38000000,
    tags: ['仙侠', '热血', '争霸'],
    similarity: 0.76,
    highlights: ['场面宏大', '群像刻画'],
  },
  {
    id: 'h6',
    title: '斗破苍穹',
    author: '天蚕土豆',
    platform: '起点中文网',
    hot_score: 90,
    read_count: 55000000,
    tags: ['玄幻', '废柴逆袭', '升级流'],
    similarity: 0.88,
    highlights: ['爽点节奏好', '金手指设定经典'],
  },
];

/** 模拟类型趋势 */
const MOCK_GENRE_TRENDS: { genre: string; score: number; change: number }[] = [
  { genre: '玄幻', score: 92, change: 5.2 },
  { genre: '都市', score: 85, change: -2.1 },
  { genre: '言情', score: 78, change: 8.4 },
  { genre: '仙侠', score: 88, change: 3.7 },
  { genre: '科幻', score: 72, change: 12.5 },
];

/** 模拟选题建议 */
const MOCK_SUGGESTIONS: {
  title: string;
  genre: string;
  score: number;
  tags: string[];
  reason: string;
}[] = [
  {
    title: '都市异能：我的系统是直播间',
    genre: '都市',
    score: 92,
    tags: ['系统流', '直播', '搞笑'],
    reason: '系统流+直播赛道持续火热，开篇Hook强，适合番茄平台快节奏',
  },
  {
    title: '修仙：从被逐出师门开始',
    genre: '仙侠',
    score: 88,
    tags: ['逆袭', '废柴流', '热血'],
    reason: '废柴逆袭经典框架经久不衰，被逐出师门提供天然悬念起点',
  },
  {
    title: '异界全职艺术家：我把地球文娱搬空',
    genre: '玄幻',
    score: 85,
    tags: ['文娱', '穿越', '爽文'],
    reason: '文娱穿越持续高热度，与地球文化结合提供无限素材库',
  },
];

/** 模拟密度柱状图数据 */
const MOCK_DENSITY: { chapter: string; count: number }[] = [
  { chapter: 'Ch.1', count: 4 },
  { chapter: 'Ch.2', count: 3 },
  { chapter: 'Ch.3', count: 5 },
  { chapter: 'Ch.4', count: 2 },
  { chapter: 'Ch.5', count: 4 },
  { chapter: 'Ch.6', count: 3 },
  { chapter: 'Ch.7', count: 6 },
  { chapter: 'Ch.8', count: 4 },
  { chapter: 'Ch.9', count: 5 },
  { chapter: 'Ch.10', count: 3 },
];

/**
 * 爆款分析中心主页面
 * 路由: /trends
 * 热门榜单 + 拆解面板 + 分析表单 + 市场预测 + 类型趋势 + 选题建议
 */
const TrendAnalysisPage: React.FC = () => {
  // 数据
  const { data: apiBenchmarks, isLoading: loadingBenchmarks } = useQualityBenchmarks();

  // 状态
  const [selectedHitId, setSelectedHitId] = useState<string | null>(null);
  const [predictionData, setPredictionData] = useState<{
    overallScore: number;
    titleFit: number;
    openingHook: number;
    marketFit: number;
    differentiation: number;
    suggestions: string[];
  } | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

  // 使用 API 数据或模拟数据
  const benchmarks: HitBenchmark[] = useMemo(
    () => (apiBenchmarks && apiBenchmarks.length > 0 ? apiBenchmarks : MOCK_HITS),
    [apiBenchmarks],
  );

  // 选中的爆款详情
  const selectedHit = useMemo(
    () => benchmarks.find((h: HitBenchmark) => h.id === selectedHitId) || null,
    [benchmarks, selectedHitId],
  );

  // 处理分析请求
  const handleAnalyze = useCallback(
    async (_data: HitAnalysisRequest) => {
      setIsAnalyzing(true);

      // 模拟分析延迟
      await new Promise((resolve) => setTimeout(resolve, 1500));

      setPredictionData({
        overallScore: Math.round(75 + Math.random() * 20),
        titleFit: Math.round(70 + Math.random() * 25),
        openingHook: Math.round(65 + Math.random() * 30),
        marketFit: Math.round(72 + Math.random() * 20),
        differentiation: Math.round(60 + Math.random() * 30),
        suggestions: [
          '标题建议增加「关键词前置」，如"都市异能"明确分类标签',
          '开头前200字建议增加一个强冲突或悬念钩子',
          '整体风格与当前热门题材「系统流」契合度高，可考虑增加系统元素',
          '人物设定建议增加更鲜明的差异化标签，如"唯一"、"最强"等',
        ],
      });
      setIsAnalyzing(false);
    },
    [],
  );

  return (
    <div className="flex flex-col gap-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <TrendingUp size={28} className="text-primary-500" />
        <h1 className="text-display text-gray-800 dark:text-gray-100">爆款分析中心</h1>
      </div>

      {/* 热门榜单卡片墙 */}
      <div>
        <h3 className="mb-3 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          🔥 热门爆款榜单
        </h3>
        {loadingBenchmarks ? (
          <div className="card flex items-center justify-center py-10">
            <LoadingSpinner text="正在加载榜单…" />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {benchmarks.slice(0, 6).map((hit: HitBenchmark, idx: number) => (
              <HitCard
                key={hit.id}
                rank={idx + 1}
                title={hit.title}
                author={hit.author}
                genre={hit.tags?.[0] || '其他'}
                hotScore={hit.hot_score}
                platform={hit.platform}
                onClick={() =>
                  setSelectedHitId(selectedHitId === hit.id ? null : hit.id)
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* 爆款拆解面板 */}
      {selectedHit && (
        <div className="card">
          <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            📊 爆款拆解 — {selectedHit.title}
          </h3>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* 标题结构分析 */}
            <div>
              <h4 className="mb-3 text-[13px] font-semibold text-gray-600 dark:text-gray-300">
                标题结构分析
              </h4>
              <div className="space-y-2">
                <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                  <span className="text-[13px] text-gray-600 dark:text-gray-400">
                    标题模式
                  </span>
                  <span className="badge badge-primary text-[11px]">
                    分类+卖点
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                  <span className="text-[13px] text-gray-600 dark:text-gray-400">
                    关键词密度
                  </span>
                  <span className="text-[13px] font-bold text-primary-500 font-mono">
                    高
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                  <span className="text-[13px] text-gray-600 dark:text-gray-400">
                    字数
                  </span>
                  <span className="text-[13px] text-gray-700 dark:text-gray-200 font-mono">
                    {selectedHit.title.length}字
                  </span>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {selectedHit.tags?.map((tag: string) => (
                    <span
                      key={tag}
                      className="badge bg-blue-50 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400 text-[11px]"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* 前10章爽点密度 */}
            <div>
              <h4 className="mb-3 text-[13px] font-semibold text-gray-600 dark:text-gray-300">
                前10章爽点密度
              </h4>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={MOCK_DENSITY}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#E2E8F0"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="chapter"
                      tick={{ fontSize: 10, fill: '#9CA3AF' }}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: '#9CA3AF' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={28}>
                      {MOCK_DENSITY.map((_entry, index: number) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={index < 3 ? '#FF6B35' : '#6366F1'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Highlight */}
          {selectedHit.highlights && selectedHit.highlights.length > 0 && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
              <p className="text-[12px] font-semibold text-amber-700 dark:text-amber-400 mb-1">
                爆款亮点
              </p>
              <ul className="space-y-0.5">
                {selectedHit.highlights.map((h: string, idx: number) => (
                  <li
                    key={idx}
                    className="text-[12px] text-amber-600 dark:text-amber-300"
                  >
                    · {h}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 分析表单 */}
      <AnalysisForm onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />

      {/* 两列布局：市场预测 + 类型趋势 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <MarketPrediction data={predictionData} isLoading={isAnalyzing} />
        <GenreTrends data={MOCK_GENRE_TRENDS} isLoading={false} />
      </div>

      {/* AI 选题建议 */}
      <TopicSuggestions
        suggestions={predictionData ? MOCK_SUGGESTIONS : []}
        isLoading={isAnalyzing}
      />
    </div>
  );
};

export default TrendAnalysisPage;
