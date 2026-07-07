import React, { useMemo } from 'react';
import { Lightbulb, ListChecks, FileEdit, CheckCircle, Send } from 'lucide-react';
import type { PipelineState } from '@/types';
import { usePipelineStatus } from '@/hooks/useApi';

interface TaskQueueProps {
  /** 可选：外部传入的 pipeline 数据（由 Dashboard 统一管理轮询） */
  pipelineData?: PipelineState;
}

interface QueueItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  iconBg: string;
  color: string;
  count: number;
  statusLabel: string;
}

/**
 * 任务队列组件
 * 使用 usePipelineStatus() 进行 5 秒轮询，展示五级队列状态
 */
const TaskQueueContent: React.FC<{ data?: PipelineState }> = ({ data }) => {
  const queueItems: QueueItem[] = useMemo(() => {
    const tasks = data?.tasks ?? [];
    const ideaCount: number = tasks.filter((t) => t.status === 'idle').length;
    const runningCount: number = tasks.filter((t) => t.status === 'running').length;
    const doneCount: number = tasks.filter((t) => t.status === 'completed').length;
    const failedCount: number = tasks.filter((t) => t.status === 'failed').length;

    return [
      {
        key: 'idea',
        label: '灵感队列',
        icon: <Lightbulb size={16} />,
        iconBg: 'bg-gray-100 dark:bg-gray-700',
        color: '#9CA3AF',
        count: ideaCount,
        statusLabel: ideaCount > 0 ? `${ideaCount} 个待处理` : '队列为空',
      },
      {
        key: 'outline',
        label: '大纲队列',
        icon: <ListChecks size={16} />,
        iconBg: 'bg-blue-50 dark:bg-blue-900/30',
        color: '#3B82F6',
        count: runningCount,
        statusLabel: runningCount > 0 ? `${runningCount} 个处理中` : '队列为空',
      },
      {
        key: 'chapter',
        label: '章节队列',
        icon: <FileEdit size={16} />,
        iconBg: 'bg-primary-50 dark:bg-primary-900/30',
        color: '#FF6B35',
        count: doneCount,
        statusLabel: doneCount > 0 ? `${doneCount} 个已完成` : '队列为空',
      },
      {
        key: 'review',
        label: '审核队列',
        icon: <CheckCircle size={16} />,
        iconBg: 'bg-amber-50 dark:bg-amber-900/30',
        color: '#F59E0B',
        count: failedCount,
        statusLabel: failedCount > 0 ? `${failedCount} 个失败` : '队列为空',
      },
      {
        key: 'publish',
        label: '发布队列',
        icon: <Send size={16} />,
        iconBg: 'bg-emerald-50 dark:bg-emerald-900/30',
        color: '#10B981',
        count: 0,
        statusLabel: '队列为空',
      },
    ];
  }, [data]);

  const totalTasks: number = data?.total ?? 0;
  const completedTasks: number = data?.completed ?? 0;
  const progressPercent: number = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  return (
    <section className="card">
      <div className="mb-4 flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700">
        <h3 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
          任务队列
        </h3>
        <span className="text-[12px] text-gray-400 dark:text-gray-500">
          {data ? `共 ${totalTasks} 个任务` : '轮询中...'}
        </span>
      </div>

      {/* 进度概览 */}
      {data && totalTasks > 0 && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-[11px] text-gray-400 dark:text-gray-500">总进度</span>
          <div className="progress flex-1">
            <div
              className="progress-bar"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="font-mono text-[12px] font-semibold text-primary-500">
            {progressPercent}%
          </span>
        </div>
      )}

      {/* 队列列表 */}
      <div className="flex flex-col gap-2">
        {queueItems.map((item: QueueItem) => (
          <div
            key={item.key}
            className={`flex cursor-pointer items-center justify-between rounded-md border px-3 py-2.5 transition-all duration-150 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:hover:border-gray-600 dark:hover:bg-gray-800 ${
              item.key === 'chapter' && item.count > 0
                ? 'border-primary-200 bg-primary-50/50 dark:border-primary-800 dark:bg-primary-900/10'
                : 'border-gray-100'
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-md ${item.iconBg}`}
              >
                <span style={{ color: item.color }}>{item.icon}</span>
              </span>
              <div>
                <p className="text-[13px] font-medium text-gray-700 dark:text-gray-200">
                  {item.label}
                </p>
                <p
                  className="text-[12px] text-gray-400 dark:text-gray-500"
                  style={item.count > 0 ? { color: item.color } : undefined}
                >
                  {item.statusLabel}
                </p>
              </div>
            </div>
            <span
              className="font-mono text-[14px] font-semibold"
              style={{ color: item.count > 0 ? item.color : '#9CA3AF' }}
            >
              {item.count}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
};

/**
 * 任务队列外层组件 — 自行管理 usePipelineStatus 轮询
 */
const TaskQueue: React.FC<TaskQueueProps> = ({ pipelineData }) => {
  // 如果外部传入了数据，直接使用；否则自行轮询
  const { data: selfData } = usePipelineStatus();

  const data: PipelineState | undefined = pipelineData ?? selfData;

  return <TaskQueueContent data={data} />;
};

export default TaskQueue;
