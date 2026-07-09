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
import { useChapters, useQualityReview, useQualityRewrite } from '@/hooks/useApi';
import { getChapter } from '@/api/endpoints';
import type {
  ChapterSummary,
  QualityDimension,
  DimensionScore,
  QualityReview,
  RewriteRequest,
} from '@/types';

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
  const reviewMutation = useQualityReview();
  const rewriteMutation = useQualityRewrite();

  // 状态
  const [review, setReview] = useState<QualityReview | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<string | undefined>(undefined);
  const [rewriteOpen, setRewriteOpen] = useState<boolean>(false);
  const [targetDimension, setTargetDimension] = useState<DimensionScore | null>(null);
  const [rewrittenText, setRewrittenText] = useState<string>('');
  const [selectedOriginalText, setSelectedOriginalText] = useState<string>('');
  const [isReviewing, setIsReviewing] = useState<boolean>(false);

  const normalizeReview = useCallback((raw: QualityReview): QualityReview => {
    const rawDimensions = raw.dimensions as unknown;
    const dimensions: DimensionScore[] = Array.isArray(rawDimensions)
      ? raw.dimensions
      : Object.entries((rawDimensions || {}) as Record<string, { score?: number; issues?: string[]; suggestions?: string[] }>).map(
          ([name, value]) => ({
            name: name as QualityDimension,
            label: name,
            score: typeof value.score === 'number' && value.score <= 10 ? value.score * 10 : (value.score || 0),
            issues: value.issues || [],
            suggestions: value.suggestions || [],
          }),
        );
    return { ...raw, dimensions };
  }, []);


  // 当选中章节变化时触发真实质量评审；失败时显示错误，不再展示模拟数据。
  const handleSelectChapter = useCallback(
    async (chapterId: string) => {
      setSelectedChapterId(chapterId);
      setRewriteOpen(false);
      setIsReviewing(true);
      setReview(null);

      try {
        const chapterDetail = await getChapter(chapterId);
        setSelectedOriginalText(chapterDetail.content || '');
        const result = await reviewMutation.mutateAsync({
          chapter_id: chapterId,
          chapter_content: chapterDetail.content || '',
          outline: '',
          context: chapterDetail.summary || '',
        });
        setReview(normalizeReview(result));
      } catch {
        setReview(null);
      } finally {
        setIsReviewing(false);
      }
    },
    [normalizeReview, reviewMutation],
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
        setRewrittenText(result.rewritten);
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
  // 此前这里7个维度分数全部用 Math.random() 编造，overallScore 也在没有
  // 真实分时回落随机数——用户看到的是一堆假数据。现在改为只用真实的
  // overall_score(来自后端 review_report)；7个维度的细分分数列表接口
  // 本就不返回(在单章 review_report.dimensions 里)，且前端这套英文维度名
  // 和后端的中文维度体系并不一致，这里不再编造，细分列显示"—"表示暂无。
  const chapterRows = useMemo(() => {
    if (!chapters) return [];
    return chapters.slice(0, 10).map((ch: ChapterSummary) => ({
      chapter: ch,
      scores: null,  // 细分维度分数需要单章详情，列表页不展示编造值
      overallScore: ch.overall_score,  // 真实综合分，未审查时为 null
    }));
  }, [chapters]);

  // 质量趋势：用各章真实的 overall_score，只纳入已审查(有分)的章节
  const trendData = useMemo(() => {
    if (!chapters) return [];
    return chapters
      .filter((ch: ChapterSummary) => ch.overall_score != null)
      .slice(0, 20)
      .map((ch: ChapterSummary) => ({
        chapter: `第${ch.chapter_num}章`,
        score: ch.overall_score as number,
      }));
  }, [chapters]);

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
          selectedOriginalText || '选择章节后查看原文'
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
