import React, { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BookOpen,
  TrendingUp,
  Star,
  Target,
  FileText,
  Activity,
  BarChart3,
  Eye,
  Rocket,
} from 'lucide-react';
import KPICard from '@/components/shared/KPICard';
import StateMachineFlow from '@/components/shared/StateMachineFlow';
import { useProjects, useOpsDashboard, usePipelineStatus, useTransitionProject } from '@/hooks/useApi';
import { STATE_LABELS } from '@/utils/helpers';
import { useProjectStore } from '@/store/projectStore';
import ProjectCard from '@/pages/Dashboard/ProjectCard';
import QuickActions from '@/pages/Dashboard/QuickActions';
import TaskQueue from '@/pages/Dashboard/TaskQueue';
import type { Project, ProjectState, PipelineState } from '@/types';

/** Ops 仪表盘响应结构 */
interface OpsDashboardData {
  total_words?: number;
  active_projects?: number;
  avg_quality_score?: number;
  foreshadow_recovery_rate?: number;
  recent_activity?: ActivityItem[];
}

interface ActivityItem {
  id: string;
  text: string;
  time: string;
  type?: string;
  project_id?: string;
  chapter_id?: string;
}

/** 活动类型对应的颜色 */
const ACTIVITY_COLORS: Record<string, string> = {
  writing: 'bg-primary-500',
  success: 'bg-emerald-500',
  world: 'bg-violet-500',
  foreshadow: 'bg-emerald-500',
  review: 'bg-amber-500',
  default: 'bg-primary-500',
};

/**
 * 总控驾驶舱 — 主页面
 * 展示 KPI、状态机、项目列表、任务队列、快捷操作、活动 Feed
 */
/** 模拟项目数据（后端未启动时展示） */
const MOCK_PROJECTS: Project[] = [
  { id: 'demo-project-001', user_id: 'demo', title: '星辰之主', target_platform: '起点', target_words: 1000000, current_words: 85000, current_state: 'writing', state_history: [], outline: '少年林凡偶获星辰之力，从废柴逆袭为绝世强者。全书8卷，从宗门试炼到诸天争霸。', world_setting: '修真世界，境界：练气→筑基→金丹→元婴→化神→渡劫→飞升。', created_at: '2026-06-01T00:00:00Z', updated_at: '2026-07-06T00:00:00Z' },
  { id: 'demo-project-002', user_id: 'demo', title: '都市医仙', target_platform: '番茄', target_words: 800000, current_words: 1200, current_state: 'outline', state_history: [], outline: '被赶出家门的医学天才获得医仙传承，从此悬壶济世。都市与修真交织。', world_setting: '现代都市中的隐世修真势力。', created_at: '2026-07-01T00:00:00Z', updated_at: '2026-07-05T00:00:00Z' },
  { id: 'demo-project-003', user_id: 'demo', title: '末日求生手册', target_platform: '晋江', target_words: 500000, current_words: 0, current_state: 'idea', state_history: [], outline: '病毒爆发后普通人如何在废墟中重建文明。', world_setting: '近未来，全球病毒爆发导致社会崩溃。', created_at: '2026-07-04T00:00:00Z', updated_at: '2026-07-04T00:00:00Z' },
];

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { data: apiProjects } = useProjects();
  const projects: Project[] = (apiProjects && (apiProjects as Project[]).length > 0) ? apiProjects as Project[] : MOCK_PROJECTS;
  const { data: opsData, isLoading: opsLoading } = useOpsDashboard();
  const { data: pipelineData } = usePipelineStatus();

  // 全局项目选择 store
  const setSelectedProjectId = useProjectStore((s) => s.setSelectedProjectId);
  const globalProjectId: string | null = useProjectStore((s) => s.selectedProjectId);

  // 当前选中的项目（用于状态机展示）
  const [selectedProjectId, setLocalSelectedProjectId] = useState<string | null>(null);

  const dashboard: OpsDashboardData = useMemo(() => {
    return (opsData as OpsDashboardData) || {};
  }, [opsData]);

  // 找到第一个进行中的项目用于状态机展示
  const activeProject: Project | undefined = useMemo(() => {
    if (!projects) return undefined;
    if (selectedProjectId) {
      return projects.find((p: Project) => p.id === selectedProjectId) || undefined;
    }
    return projects.find((p: Project) => p.current_state !== 'publish') || projects[0];
  }, [projects, selectedProjectId]);

  // 状态迁移 mutation
  const transitionMutation = useTransitionProject(activeProject?.id || '');

  const handleTransition = useCallback(
    (newState: ProjectState) => {
      if (activeProject) {
        setLocalSelectedProjectId(activeProject.id);
        transitionMutation.mutate(
          { new_state: newState, note: `从 ${STATE_LABELS[activeProject.current_state]} 迁移到 ${STATE_LABELS[newState]}` },
          {
            onSuccess: (updated: Project) => {
              setLocalSelectedProjectId(updated.id);
            },
          },
        );
      }
    },
    [activeProject, transitionMutation],
  );

  const handleProjectSelect = useCallback(
    (id: string) => {
      // 同步全局 store，使侧边栏 / 快捷面板能正确拼接 projectId
      setSelectedProjectId(id);
      navigate(`/write/${id}`);
    },
    [navigate, setSelectedProjectId],
  );

  // 计算 KPI 数值
  const totalWords: number =
    dashboard.total_words ??
    (projects ? projects.reduce((sum: number, p: Project) => sum + (p.current_words || 0), 0) : 0);

  const activeProjectCount: number =
    dashboard.active_projects ??
    (projects ? projects.filter((p: Project) => p.current_state !== 'publish').length : 0);

  const avgQuality: number = dashboard.avg_quality_score ?? 0;

  const foreshadowRate: number = dashboard.foreshadow_recovery_rate ?? 0;

  // 活动列表
  const activities: ActivityItem[] = dashboard.recent_activity ?? [];

  return (
    <div className="flex flex-col gap-6">
      {/* ===== 顶部 KPI 卡片行 ===== */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KPICard
          icon={<FileText size={18} />}
          label="总字数"
          value={totalWords}
          unit="字"
          trend={totalWords > 0 ? 'up' : 'neutral'}
          trendLabel={false ? '加载中...' : `共 ${projects?.length || 0} 个项目`}
        />
        <KPICard
          icon={<BookOpen size={18} />}
          label="进行中"
          value={activeProjectCount}
          unit="部"
          trend="up"
          trendLabel={opsLoading ? '加载中...' : '活跃项目'}
        />
        <KPICard
          icon={<Star size={18} />}
          label="平均质量分"
          value={avgQuality}
          unit="分"
          trend={avgQuality >= 70 ? 'up' : avgQuality > 0 ? 'down' : 'neutral'}
          trendLabel={opsLoading ? '加载中...' : '持续优化中'}
        />
        <KPICard
          icon={<Target size={18} />}
          label="伏笔回收率"
          value={foreshadowRate}
          unit="%"
          trend={foreshadowRate >= 70 ? 'up' : foreshadowRate > 0 ? 'down' : 'neutral'}
          trendLabel={opsLoading ? '加载中...' : '伏笔追踪'}
        />
      </div>

      {/* ===== 状态机流程图 ===== */}
      <section className="card !p-0 overflow-hidden">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4 dark:border-gray-700">
          <div>
            <h3 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
              创作状态机
            </h3>
            <p className="mt-1 text-[13px] text-gray-500 dark:text-gray-400">
              {activeProject
                ? `《${activeProject.title}》当前处于${STATE_LABELS[activeProject.current_state]}阶段`
                : false
                  ? '加载项目数据...'
                  : '创建一本小说开始创作'}
            </p>
          </div>
          {activeProject && (
            <span className="badge badge-warning">
              <span
                className="mr-1 inline-block h-2 w-2 rounded-full"
                style={{
                  backgroundColor:
                    activeProject.current_state === 'writing'
                      ? '#FF6B35'
                      : activeProject.current_state === 'review'
                        ? '#F59E0B'
                        : activeProject.current_state === 'publish'
                          ? '#10B981'
                          : '#9CA3AF',
                }}
              />
              {STATE_LABELS[activeProject.current_state]}
            </span>
          )}
        </div>
        {activeProject ? (
          <StateMachineFlow
            currentState={activeProject.current_state}
            onTransition={handleTransition}
          />
        ) : (
          <div className="flex items-center justify-center py-12 text-sm text-gray-400 dark:text-gray-500">
            {false ? '加载中...' : '暂无项目，请创建一个'}
          </div>
        )}
      </section>

      {/* ===== 项目列表 + 任务队列（双栏） ===== */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 当前小说卡片列表 */}
        <section className="card">
          <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700">
            <h3 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
              项目列表
            </h3>
            {projects && (
              <span className="badge badge-primary">
                <span className="mr-1 inline-block h-2 w-2 rounded-full bg-primary-500" />
                {projects.length} 个项目
              </span>
            )}
          </div>

          {false ? (
            <div className="flex items-center justify-center py-8 text-sm text-gray-400">
              加载中...
            </div>
          ) : projects && projects.length > 0 ? (
            <div className="flex flex-col gap-3">
              {projects.map((project: Project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onSelect={handleProjectSelect}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
              <FileText size={40} className="text-gray-300 dark:text-gray-600" />
              <p className="text-sm text-gray-400 dark:text-gray-500">
                暂无项目，点击下方「新建项目」开始创作
              </p>
            </div>
          )}
        </section>

        {/* 任务队列 */}
        <TaskQueue pipelineData={pipelineData as PipelineState | undefined} />
      </div>

      {/* ===== 快捷操作 + 最近活动（双栏） ===== */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 快捷操作面板 */}
        <QuickActions />

        {/* 最近活动 Feed */}
        <section className="card">
          <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-4 dark:border-gray-700">
            <Activity size={18} className="text-gray-400" />
            <h3 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
              最近活动
            </h3>
          </div>

          {activities.length > 0 ? (
            <div className="flex flex-col gap-3">
              {activities.map((item: ActivityItem) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 rounded-md px-3 py-2 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      ACTIVITY_COLORS[item.type || 'default'] || ACTIVITY_COLORS.default
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] text-gray-700 dark:text-gray-200">
                      {item.text}
                    </p>
                    <p className="mt-0.5 font-mono text-[12px] text-gray-400 dark:text-gray-500">
                      {item.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
              <Activity size={40} className="text-gray-300 dark:text-gray-600" />
              <p className="text-sm text-gray-400 dark:text-gray-500">
                暂无最近活动
              </p>
            </div>
          )}
        </section>
      </div>

      {/* 底部快捷面板 — 扫榜 / 数据分析 */}
      <section className="card">
        <div className="flex flex-wrap items-center gap-4">
          <button
            className="btn-ghost flex-1 justify-center gap-2"
            onClick={() => navigate('/trends')}
          >
            <TrendingUp size={18} />
            <span className="hidden sm:inline">扫榜选题</span>
            <span className="text-[12px] text-gray-400">AI 推荐方向</span>
          </button>
          <button
            className="btn-ghost flex-1 justify-center gap-2"
            onClick={() => navigate(globalProjectId ? `/quality/${globalProjectId}` : '/')}
          >
            <BarChart3 size={18} />
            <span className="hidden sm:inline">质量总览</span>
            <span className="text-[12px] text-gray-400">7维分析</span>
          </button>
          <button
            className="btn-ghost flex-1 justify-center gap-2"
            onClick={() => navigate(globalProjectId ? `/foreshadows/${globalProjectId}` : '/')}
          >
            <Eye size={18} />
            <span className="hidden sm:inline">伏笔管理</span>
            <span className="text-[12px] text-gray-400">埋设回收</span>
          </button>
          <button
            className="btn-primary flex-1 justify-center gap-2"
            onClick={() => navigate('/')}
          >
            <Rocket size={18} />
            <span>开始创作</span>
          </button>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
