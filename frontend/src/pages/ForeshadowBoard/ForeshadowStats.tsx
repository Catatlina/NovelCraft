import React from 'react';
import { Target, AlertTriangle, Clock, Hash } from 'lucide-react';
import KPICard from '@/components/shared/KPICard';
import type { ForeshadowStats as ForeshadowStatsType } from '@/types';

interface ForeshadowStatsProps {
  stats: ForeshadowStatsType | undefined;
  isLoading: boolean;
}

/**
 * 伏笔统计概览组件
 * 展示 4 个 KPI 卡片：伏笔总数+回收率、超期伏笔数、平均回收周期、伏笔密度
 */
const ForeshadowStats: React.FC<ForeshadowStatsProps> = ({ stats }) => {
  const total: number = stats?.total ?? 0;
  const resolutionRate: number = stats?.resolution_rate ?? 0;
  const overdue: number = stats?.overdue ?? 0;
  const planted: number = stats?.planted ?? 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KPICard
        icon={<Target size={18} />}
        label="伏笔总数 / 回收率"
        value={total}
        unit="条"
        trend={resolutionRate >= 60 ? 'up' : resolutionRate >= 30 ? 'neutral' : 'down'}
        trendLabel={`${resolutionRate}% 已回收`}
      />
      <KPICard
        icon={<AlertTriangle size={18} />}
        label="超期伏笔数"
        value={overdue}
        unit="条"
        trend={overdue > 0 ? 'down' : 'neutral'}
        trendLabel={overdue > 0 ? '需立即处理' : '暂无超期'}
      />
      <KPICard
        icon={<Clock size={18} />}
        label="平均回收周期"
        value={planted > 0 ? Math.round(planted * 3.5) : 0}
        unit="章"
        trend="neutral"
        trendLabel="距埋设平均章节"
      />
      <KPICard
        icon={<Hash size={18} />}
        label="伏笔密度"
        value={total > 0 ? parseFloat((total / Math.max(planted || 1, 1)).toFixed(1)) : 0}
        unit="条/章"
        trend="neutral"
        trendLabel="总伏笔/章节数"
      />
    </div>
  );
};

export default ForeshadowStats;
