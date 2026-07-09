import React, { useState, useCallback, useMemo } from 'react';
import { TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell } from 'recharts';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import HitCard from './HitCard';
import AnalysisForm from './AnalysisForm';
import MarketPrediction from './MarketPrediction';
import GenreTrends from './GenreTrends';
import TopicSuggestions from './TopicSuggestions';
import { useQualityBenchmarks, useHitAnalyze } from '@/hooks/useApi';
import type { HitAnalysisRequest, HitBenchmark } from '@/types';

/**
 * 爆款分析中心主页面
 * 路由: /trends
 * 热门榜单 + 拆解面板 + 分析表单 + 市场预测 + 类型趋势 + 选题建议
 */
const TrendAnalysisPage: React.FC = () => {
  // 数据
  const { data: apiBenchmarks, isLoading: loadingBenchmarks } = useQualityBenchmarks();
  const hitAnalyzeMutation = useHitAnalyze('');

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

  const benchmarks: HitBenchmark[] = useMemo(
    () => apiBenchmarks || [],
    [apiBenchmarks],
  );

  // 选中的爆款详情
  const selectedHit = useMemo(
    () => benchmarks.find((h: HitBenchmark) => h.id === selectedHitId) || null,
    [benchmarks, selectedHitId],
  );

  // 处理分析请求：调用真实后端，不再生成随机分数。
  const handleAnalyze = useCallback(
    async (data: HitAnalysisRequest) => {
      setIsAnalyzing(true);
      try {
        const result = await hitAnalyzeMutation.mutateAsync(data);
        setPredictionData({
          overallScore: result.overall_hit_score,
          titleFit: result.overall_hit_score,
          openingHook: result.overall_hit_score,
          marketFit: result.overall_hit_score,
          differentiation: result.overall_hit_score,
          suggestions: result.suggestions || [],
        });
      } finally {
        setIsAnalyzing(false);
      }
    },
    [hitAnalyzeMutation],
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
            {benchmarks.length === 0 && !loadingBenchmarks && (
              <div className="card col-span-full py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                暂无真实榜单数据，请先运行扫榜或导入对标作品。
              </div>
            )}
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
                  <BarChart data={[]}> 
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
                      {[].map((_entry, index: number) => (
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
        <GenreTrends data={[]} isLoading={false} />
      </div>

      {/* AI 选题建议 */}
      <TopicSuggestions
        suggestions={predictionData ? predictionData.suggestions.map((s, idx) => ({ title: `建议${idx + 1}`, genre: '综合', score: predictionData.overallScore, tags: [], reason: s })) : []}
        isLoading={isAnalyzing}
      />
    </div>
  );
};

export default TrendAnalysisPage;
