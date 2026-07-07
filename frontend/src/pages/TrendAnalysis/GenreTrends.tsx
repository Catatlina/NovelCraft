import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface GenreTrend {
  genre: string;
  score: number;
  change: number; // 涨跌百分比
}

interface GenreTrendsProps {
  data: GenreTrend[];
  isLoading: boolean;
}

const CHART_COLORS: string[] = [
  '#FF6B35', '#FF2442', '#6366F1', '#10B981', '#F59E0B',
];

/**
 * 热门类型趋势柱状图
 * Recharts BarChart + 涨跌标记
 */
const GenreTrends: React.FC<GenreTrendsProps> = ({ data, isLoading }) => {
  if (isLoading) {
    return (
      <div className="card">
        <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          热门类型趋势
        </h3>
        <div className="flex items-center justify-center py-10">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-200 border-t-primary-500" />
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="card">
        <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
          热门类型趋势
        </h3>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <p className="text-[13px] text-gray-400 dark:text-gray-500">暂无趋势数据</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
        热门类型趋势
      </h3>

      {/* 柱状图 */}
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis
              dataKey="genre"
              tick={{ fontSize: 12, fill: '#6B7280' }}
              axisLine={{ stroke: '#E2E8F0' }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: '#9CA3AF' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                borderRadius: '8px',
                border: '1px solid #E2E8F0',
                fontSize: '13px',
              }}
              formatter={(value: number) => [`${value} 热度`, '热度指数']}
            />
            <Bar dataKey="score" radius={[6, 6, 0, 0]} maxBarSize={48}>
              {data.map((_entry: GenreTrend, index: number) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 涨跌列表 */}
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {data.map((item: GenreTrend, idx: number) => (
          <div
            key={item.genre}
            className="flex items-center gap-2 rounded-lg border border-gray-200 p-2 dark:border-gray-700"
          >
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
            />
            <span className="text-[12px] font-medium text-gray-700 dark:text-gray-200">
              {item.genre}
            </span>
            <span
              className={`ml-auto flex items-center gap-0.5 text-[11px] font-mono font-semibold ${
                item.change >= 0
                  ? 'text-emerald-500 dark:text-emerald-400'
                  : 'text-red-500 dark:text-red-400'
              }`}
            >
              {item.change >= 0 ? (
                <TrendingUp size={11} />
              ) : (
                <TrendingDown size={11} />
              )}
              {item.change >= 0 ? '+' : ''}
              {item.change}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default GenreTrends;
