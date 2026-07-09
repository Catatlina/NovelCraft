import React, { useState, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { LayoutGrid, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import ForeshadowStats from './ForeshadowStats';
import ForeshadowFilters from './ForeshadowFilters';
import ForeshadowColumn from './ForeshadowColumn';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import { fsCheckPayoff } from '@/api/endpoints';
import {
  useForeshadows,
  useForeshadowStats,
  useAutoCheckOverdue,
  queryKeys,
} from '@/hooks/useApi';
import type { Foreshadow, ForeshadowStatus } from '@/types';

/**
 * 伏笔看板主页面
 * 路由: /foreshadows/:projectId
 * 三列看板布局：未回收（planted）、已回收（paid_off）、超期（overdue）
 */
const ForeshadowBoardPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<ForeshadowStatus | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [, setCheckingIds] = useState<Set<string>>(new Set());

  // 数据获取
  const {
    data: foreshadows,
    isLoading: loadingForeshadows,
  } = useForeshadows(projectId);

  const {
    data: stats,
    isLoading: loadingStats,
  } = useForeshadowStats(projectId);

  // Mutations
  const checkOverdueMutation = useAutoCheckOverdue(projectId || '');

  // 单条 AI 检查伏笔回收
  // TODO(产品设计缺口): 后端 /check-payoff 要求传入实际回收该伏笔的章节正文才能做 AI 质量分析，
  // 当前 UI 没有一个专门的输入框收集这段文本。这里用 window.prompt 做最小可用过渡，
  // 后续应替换成一个真正的弹窗，让用户选择/粘贴对应章节内容。
  const handleCheckPayoff = useCallback(
    async (foreshadowId: string) => {
      const chapterContent = window.prompt('请粘贴回收该伏笔的章节正文，用于 AI 质量分析：');
      if (!chapterContent) return;
      setCheckingIds((prev) => new Set(prev).add(foreshadowId));
      try {
        await fsCheckPayoff(foreshadowId, chapterContent);
        toast.success('伏笔回收检查完成');
        if (projectId) {
          queryClient.invalidateQueries({ queryKey: queryKeys.foreshadows(projectId) });
          queryClient.invalidateQueries({ queryKey: queryKeys.foreshadowStats(projectId) });
        }
      } catch {
        toast.error('检查失败，请稍后重试');
      } finally {
        setCheckingIds((prev) => {
          const next = new Set(prev);
          next.delete(foreshadowId);
          return next;
        });
      }
    },
    [projectId, queryClient],
  );

  // 标记回收
  // TODO(产品设计缺口): 后端目前没有一个"仅标记为已回收、不做AI分析"的独立接口，
  // 只能复用同一个 /check-payoff 接口，同样需要章节正文，见上方TODO。
  const handleMarkPayoff = useCallback(
    async (foreshadowId: string) => {
      const chapterContent = window.prompt('请粘贴回收该伏笔的章节正文：');
      if (!chapterContent) return;
      setCheckingIds((prev) => new Set(prev).add(foreshadowId));
      try {
        await fsCheckPayoff(foreshadowId, chapterContent);
        toast.success('已标记为回收');
        if (projectId) {
          queryClient.invalidateQueries({ queryKey: queryKeys.foreshadows(projectId) });
          queryClient.invalidateQueries({ queryKey: queryKeys.foreshadowStats(projectId) });
        }
      } catch {
        toast.error('操作失败，请稍后重试');
      } finally {
        setCheckingIds((prev) => {
          const next = new Set(prev);
          next.delete(foreshadowId);
          return next;
        });
      }
    },
    [projectId, queryClient],
  );

  const handleCheckOverdue = useCallback(() => {
    if (projectId) {
      checkOverdueMutation.mutate(undefined as void);
    }
  }, [projectId, checkOverdueMutation]);

  // 按状态分组 + 搜索过滤
  const grouped = useMemo(() => {
    if (!foreshadows) return { planted: [], paid_off: [], overdue: [] };

    let filtered: Foreshadow[] = foreshadows;

    // 状态筛选
    if (statusFilter !== 'all') {
      filtered = filtered.filter((f: Foreshadow) => f.status === statusFilter);
    }

    // 搜索过滤
    if (searchTerm.trim()) {
      const term: string = searchTerm.trim().toLowerCase();
      filtered = filtered.filter(
        (f: Foreshadow) =>
          f.content.toLowerCase().includes(term) ||
          (f.note && f.note.toLowerCase().includes(term)),
      );
    }

    return {
      planted: filtered.filter((f: Foreshadow) => f.status === 'planted'),
      paid_off: filtered.filter((f: Foreshadow) => f.status === 'paid_off'),
      overdue: filtered.filter((f: Foreshadow) => f.status === 'overdue'),
    };
  }, [foreshadows, statusFilter, searchTerm]);

  // Loading state
  if (loadingForeshadows && !foreshadows) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-display text-gray-800 dark:text-gray-100">伏笔看板</h1>
        <LoadingSpinner size="lg" text="正在加载伏笔数据…" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-3">
        <LayoutGrid size={28} className="text-primary-500" />
        <h1 className="text-display text-gray-800 dark:text-gray-100">伏笔看板</h1>
      </div>

      {/* KPI 统计卡片 */}
      <ForeshadowStats stats={stats} isLoading={loadingStats} />

      {/* 筛选栏 */}
      <ForeshadowFilters
        statusFilter={statusFilter}
        searchTerm={searchTerm}
        onStatusChange={setStatusFilter}
        onSearchChange={setSearchTerm}
        onCheckOverdue={handleCheckOverdue}
        isCheckingOverdue={checkOverdueMutation.isPending}
      />

      {/* 三列看板布局 */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <ForeshadowColumn
          title="未回收"
          count={grouped.planted.length}
          foreshadows={grouped.planted}
          color="orange"
          icon={<Clock size={16} />}
          onMarkPayoff={handleMarkPayoff}
          onCheckPayoff={handleCheckPayoff}
        />
        <ForeshadowColumn
          title="已回收"
          count={grouped.paid_off.length}
          foreshadows={grouped.paid_off}
          color="green"
          icon={<CheckCircle2 size={16} />}
        />
        <ForeshadowColumn
          title="超期"
          count={grouped.overdue.length}
          foreshadows={grouped.overdue}
          color="red"
          icon={<AlertCircle size={16} />}
          onCheckPayoff={handleCheckPayoff}
        />
      </div>
    </div>
  );
};

export default ForeshadowBoardPage;
