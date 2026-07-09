/**
 * AnalyticsDashboard — 数据分析看板
 * 路由: /analytics
 *
 * Phase 9.1: 数据分析
 * KPI 卡片、趋势图、平台对比雷达图、章节版本履历
 * 调用 GET /api/v1/analytics/dashboard
 */
import React, { useState, useCallback } from 'react';
import {
  BarChart3,
  Eye,
  BookOpen,
  ThumbsUp,
  Calendar,
  RefreshCw,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import KPICard from '@/components/shared/KPICard';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import { useProjects } from '@/hooks/useApi';
import { api } from '@/api/client';

// ============================================================
// Types
// ============================================================

interface DashboardData {
  kpis: {
    total_views: number;
    total_chapters: number;
    avg_rating: number;
    total_projects: number;
    views_change_pct: number;
    chapters_change_pct: number;
    rating_change_pct: number;
    projects_change_pct: number;
  };
  trend: Array<{ date: string; views: number; chapters: number }>;
  platform_comparison: Array<{
    platform: string;
    readability: number;
    engagement: number;
    consistency: number;
    marketability: number;
  }>;
}

const TIME_RANGES = [
  { value: '7d', label: '7天' },
  { value: '30d', label: '30天' },
  { value: '90d', label: '90天' },
];

const AnalyticsDashboard: React.FC = () => {
  // ---- 状态 ----
  const [timeRange, setTimeRange] = useState<string>('30d');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const { data: projects } = useProjects();

  // ---- 数据获取 ----
  const fetchDashboard = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const params: string[] = [];
      if (timeRange) params.push(`time_range=${encodeURIComponent(timeRange)}`);
      if (selectedProjectId) params.push(`project_id=${encodeURIComponent(selectedProjectId)}`);
      const query: string = params.length > 0 ? `?${params.join('&')}` : '';
      const data: DashboardData = await api<DashboardData>(
        `/analytics/dashboard${query}`,
        'GET',
      );
      setDashboardData(data);
    } catch {
      setError('数据加载失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [timeRange, selectedProjectId]);

  // 首次自动加载
  React.useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // ---- 派生 ----
  const data: DashboardData | null = dashboardData;

  if (!data && !loading) {
    return (
      <div className="flex h-full items-center justify-center text-gray-500">
        {error || '暂无分析数据'}
      </div>
    );
  }

  if (!data) return <LoadingSpinner />;

  // ---- 渲染 ----
  return (
    <div className="flex flex-col gap-6">
      {/* 页面标题 + 操作栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <BarChart3 size={28} className="text-primary-500" />
          <h1 className="text-display text-gray-800 dark:text-gray-100">数据分析看板</h1>
        </div>

        <div className="flex items-center gap-2">
          {/* 项目筛选 */}
          <select
            value={selectedProjectId}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setSelectedProjectId(e.target.value)
            }
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-[12px] text-gray-700 focus:border-primary-400 focus:outline-none dark:border-gray-600 dark:bg-dark-surface dark:text-gray-200"
          >
            <option value="">全部项目</option>
            {(projects || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>

          {/* 时间范围 */}
          <div className="flex rounded-lg border border-gray-200 dark:border-gray-600 overflow-hidden">
            {TIME_RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => setTimeRange(r.value)}
                className={`px-3 py-2 text-[12px] font-medium transition-colors ${
                  timeRange === r.value
                    ? 'bg-primary-500 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50 dark:bg-dark-surface dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          {/* 刷新 */}
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-[12px] text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-dark-surface dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
            aria-label="刷新数据"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            刷新
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-10">
          <LoadingSpinner size="md" text="加载数据中…" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-[12px] text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* KPI 卡片行 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          icon={<Eye size={18} />}
          label="总阅读量"
          value={data.kpis.total_views}
          trend={data.kpis.views_change_pct >= 0 ? 'up' : 'down'}
          trendLabel={`${data.kpis.views_change_pct >= 0 ? '+' : ''}${data.kpis.views_change_pct}% 较上周`}
        />
        <KPICard
          icon={<BookOpen size={18} />}
          label="总章节数"
          value={data.kpis.total_chapters}
          unit="章"
          trend={data.kpis.chapters_change_pct >= 0 ? 'up' : 'down'}
          trendLabel={`${data.kpis.chapters_change_pct >= 0 ? '+' : ''}${data.kpis.chapters_change_pct}% 较上周`}
        />
        <KPICard
          icon={<ThumbsUp size={18} />}
          label="平均评分"
          value={data.kpis.avg_rating}
          unit="分"
          trend={data.kpis.rating_change_pct >= 0 ? 'up' : 'down'}
          trendLabel={`${data.kpis.rating_change_pct >= 0 ? '+' : ''}${data.kpis.rating_change_pct}% 较上周`}
        />
        <KPICard
          icon={<BarChart3 size={18} />}
          label="项目总数"
          value={data.kpis.total_projects}
          unit="个"
          trend="neutral"
          trendLabel="持平"
        />
      </div>

      {/* 趋势图 + 雷达图 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 趋势图 */}
        <div className="card p-5">
          <h3 className="mb-4 flex items-center gap-2 text-[14px] font-semibold text-gray-700 dark:text-gray-200">
            <Calendar size={16} className="text-primary-500" />
            阅读 & 产出趋势
          </h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
                <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: '1px solid #E2E8F0',
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12 }}
                  iconType="circle"
                />
                <Line
                  type="monotone"
                  dataKey="views"
                  name="阅读量"
                  stroke="#6366F1"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#6366F1' }}
                  activeDot={{ r: 6 }}
                />
                <Line
                  type="monotone"
                  dataKey="chapters"
                  name="章节数"
                  stroke="#FF6B35"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#FF6B35' }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 平台对比雷达图 */}
        <div className="card p-5">
          <h3 className="mb-4 flex items-center gap-2 text-[14px] font-semibold text-gray-700 dark:text-gray-200">
            <BarChart3 size={16} className="text-primary-500" />
            平台质量对比
          </h3>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={data.platform_comparison}>
                <PolarGrid stroke="#E2E8F0" />
                <PolarAngleAxis
                  dataKey="platform"
                  tick={{ fontSize: 10, fill: '#9CA3AF' }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, 100]}
                  tick={{ fontSize: 9, fill: '#9CA3AF' }}
                />
                <Radar
                  name="可读性"
                  dataKey="readability"
                  stroke="#6366F1"
                  fill="#6366F1"
                  fillOpacity={0.15}
                />
                <Radar
                  name="吸引力"
                  dataKey="engagement"
                  stroke="#FF6B35"
                  fill="#FF6B35"
                  fillOpacity={0.15}
                />
                <Radar
                  name="一致性"
                  dataKey="consistency"
                  stroke="#10B981"
                  fill="#10B981"
                  fillOpacity={0.15}
                />
                <Radar
                  name="市场性"
                  dataKey="marketability"
                  stroke="#F59E0B"
                  fill="#F59E0B"
                  fillOpacity={0.15}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11 }}
                  iconType="circle"
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 章节版本 & 趋势柱状图 */}
      <div className="card p-5">
        <h3 className="mb-4 flex items-center gap-2 text-[14px] font-semibold text-gray-700 dark:text-gray-200">
          <BookOpen size={16} className="text-primary-500" />
          各项目产出统计
        </h3>
        <div className="h-[240px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={[
                { name: '星辰之海', chapters: 86, reviews: 124 },
                { name: '时间猎手', chapters: 52, reviews: 78 },
                { name: '雨巷深处', chapters: 94, reviews: 203 },
                { name: '异界直播间', chapters: 38, reviews: 45 },
              ]}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9CA3AF' }} />
              <YAxis tick={{ fontSize: 11, fill: '#9CA3AF' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: '1px solid #E2E8F0',
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} iconType="rect" />
              <Bar dataKey="chapters" name="章节数" fill="#6366F1" radius={[4, 4, 0, 0]} maxBarSize={36} />
              <Bar dataKey="reviews" name="评审数" fill="#FF6B35" radius={[4, 4, 0, 0]} maxBarSize={36} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
