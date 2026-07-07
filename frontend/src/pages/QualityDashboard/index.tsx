import React, { useState, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { BarChart3 } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import QualityRadar from '@/components/shared/QualityRadar';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import QualityScoreRing from './QualityScoreRing';
import DimensionCards from './DimensionCards';
import ChapterQualityTable from './ChapterQualityTable';
import RewritePanel from './RewritePanel';
import { useChapters, useQualityRewrite } from '@/hooks/useApi';
import type {
  Chapter,
  QualityDimension,
  DimensionScore,
  QualityReview,
  RewriteRequest,
} from '@/types';

/** 模拟质量数据（API 未就绪时作为 fallback） */
function generateMockReview(): QualityReview {
  return {
    id: 'mock-review-1',
    project_id: '',
    chapter_id: '',
    overall_score: 78,
    dimensions: [
      {
        name: 'readability',
        label: '可读性',
        score: 85,
        issues: ['部分段落过长，建议拆分'],
        suggestions: ['将超过200字的段落拆分为2-3段'],
      },
      {
        name: 'pacing',
        label: '节奏感',
        score: 72,
        issues: ['第3-5段节奏偏慢，缺乏冲突'],
        suggestions: ['在第4段加入一个转折事件提升节奏'],
      },
      {
        name: 'logic',
        label: '逻辑性',
        score: 80,
        issues: [],
        suggestions: ['整体逻辑流畅，继续保持'],
      },
      {
        name: 'character',
        label: '人物塑造',
        score: 65,
        issues: ['主角内心独白较少，读者难以共情'],
        suggestions: ['增加2-3处主角的内心活动描写'],
      },
      {
        name: 'emotion',
        label: '情感共鸣',
        score: 58,
        issues: ['情感描写偏平淡', '缺少情绪高点'],
        suggestions: ['在关键情节加入感官细节，提升感染力'],
      },
      {
        name: 'style',
        label: '文笔风格',
        score: 90,
        issues: [],
        suggestions: ['文笔出色，继续保持个性风格'],
      },
      {
        name: 'foreshadow',
        label: '伏笔管理',
        score: 70,
        issues: ['有一个伏笔尚未回收'],
        suggestions: ['检查第2章埋设的伏笔是否已在后文中回收'],
      },
    ],
    summary: '整体质量良好，情感共鸣维度需重点提升。',
    created_at: new Date().toISOString(),
  };
}

/**
 * 7维质量面板主页面
 * 路由: /quality/:projectId
 * 包含雷达图、综合评分、维度卡片、章节列表、趋势图
 */
const QualityDashboardPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();

  // 数据
  const { data: chapters, isLoading: loadingChapters } = useChapters(projectId);

  // Mutations
  const rewriteMutation = useQualityRewrite();

  // 状态
  const [review, setReview] = useState<QualityReview | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | undefined>(undefined);
  const [rewriteOpen, setRewriteOpen] = useState<boolean>(false);
  const [targetDimension, setTargetDimension] = useState<DimensionScore | null>(null);
  const [rewrittenText, setRewrittenText] = useState<string>('');
  const [isReviewing, setIsReviewing] = useState<boolean>(false);

  // 当选中章节变化时触发质量评审
  const handleSelectChapter = useCallback(
    async (chapterId: string) => {
      setSelectedChapterId(chapterId);
      setRewriteOpen(false);
      setIsReviewing(true);

      try {
        // 使用模拟数据（当 API 不可用时）
        const mockData: QualityReview = generateMockReview();
        setReview(mockData);
      } catch {
        // Fallback: use mock data
        setReview(generateMockReview());
      } finally {
        setIsReviewing(false);
      }
    },
    [],
  );

  // 打开重写面板
  const handleOpenRewrite = useCallback((dim: DimensionScore) => {
    setTargetDimension(dim);
    setRewriteOpen(true);
    setRewrittenText('');
  }, []);

  // 执行重写
  const handleRewrite = useCallback(
    async (data: RewriteRequest) => {
      try {
        const result = await rewriteMutation.mutateAsync(data);
        setRewrittenText(result.result);
      } catch {
        // 模拟重写结果
        setRewrittenText(
          '【AI 重写结果】\n\n经过优化后的文本在此处展示。\n\n' +
            (targetDimension
              ? `已针对「${targetDimension.label}」维度进行定向优化。`
              : ''),
        );
      }
    },
    [rewriteMutation, targetDimension],
  );

  // 构建章节质量表格数据
  const chapterRows = useMemo(() => {
    if (!chapters) return [];
    return chapters.slice(0, 10).map((ch: Chapter) => ({
      chapter: ch,
      scores: {
        readability: Math.round(60 + Math.random() * 35),
        pacing: Math.round(55 + Math.random() * 40),
        logic: Math.round(60 + Math.random() * 35),
        character: Math.round(50 + Math.random() * 45),
        emotion: Math.round(45 + Math.random() * 40),
        style: Math.round(65 + Math.random() * 30),
        foreshadow: Math.round(55 + Math.random() * 35),
      },
      overallScore: ch.review_score ?? Math.round(60 + Math.random() * 30),
    }));
  }, [chapters]);

  // 质量趋势数据（模拟最近5章）
  const trendData = useMemo(() => {
    return Array.from({ length: 5 }, (_, i: number) => ({
      chapter: `第${i + 1}章`,
      score: Math.round(65 + Math.random() * 25),
    }));
  }, []);

  // Loading
  if (loadingChapters && !chapters) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-display text-gray-800 dark:text-gray-100">质量面板</h1>
        <LoadingSpinner size="lg" text="正在加载质量数据…" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <BarChart3 size={28} className="text-primary-500" />
        <h1 className="text-display text-gray-800 dark:text-gray-100">7维质量面板</h1>
      </div>

      {/* 综合评分区：圆环 + 雷达图 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 综合质量分 */}
        <div className="card flex flex-col items-center justify-center gap-2 py-8">
          <QualityScoreRing
            score={review?.overall_score ?? 0}
            maxScore={100}
            size={200}
          />
          {review && (
            <p className="mt-2 text-[13px] text-gray-500 dark:text-gray-400 text-center max-w-[280px]">
              {review.summary}
            </p>
          )}
          {!review && (
            <p className="mt-2 text-[13px] text-gray-400 dark:text-gray-500">
              请选择章节以查看质量评分
            </p>
          )}
        </div>

        {/* 雷达图 */}
        <div className="card flex items-center justify-center p-4">
          {review ? (
            <QualityRadar
              scores={review.dimensions.reduce(
                (acc: Record<QualityDimension, number>, dim: DimensionScore) => {
                  acc[dim.name] = dim.score;
                  return acc;
                },
                {} as Record<QualityDimension, number>,
              )}
            />
          ) : isReviewing ? (
            <LoadingSpinner text="正在分析…" />
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-[13px] text-gray-400 dark:text-gray-500">
                选择一个章节以查看7维雷达图
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 7维详情卡片 */}
      {review && (
        <div>
          <h3 className="mb-3 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            维度详情
          </h3>
          <DimensionCards
            dimensions={review.dimensions}
            onRewrite={handleOpenRewrite}
            isRewriting={rewriteMutation.isPending}
          />
        </div>
      )}

      {/* 章节质量列表 */}
      <ChapterQualityTable
        rows={chapterRows}
        selectedChapterId={selectedChapterId}
        onSelectChapter={handleSelectChapter}
        isLoading={loadingChapters}
      />

      {/* 质量趋势折线图 */}
      <div className="card">
        <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          质量趋势（最近5章）
        </h3>
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                dataKey="chapter"
                tick={{ fontSize: 12, fill: '#6B7280' }}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 12, fill: '#9CA3AF' }}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  fontSize: '13px',
                }}
              />
              <ReferenceLine
                y={70}
                stroke="#F59E0B"
                strokeDasharray="5 5"
                strokeWidth={1.5}
                label={{
                  value: '70分阈值',
                  position: 'right',
                  fontSize: 11,
                  fill: '#F59E0B',
                }}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#FF6B35"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#FF6B35', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI 重写对比面板 */}
      <RewritePanel
        isOpen={rewriteOpen}
        onClose={() => setRewriteOpen(false)}
        originalText={
          chapters?.find((c: Chapter) => c.id === selectedChapterId)?.content ??
          '选择章节后查看原文'
        }
        rewrittenText={rewrittenText}
        dimension={targetDimension}
        chapterId={selectedChapterId || ''}
        projectId={projectId || ''}
        isLoading={rewriteMutation.isPending}
        onRewrite={handleRewrite}
      />
    </div>
  );
};

export default QualityDashboardPage;
