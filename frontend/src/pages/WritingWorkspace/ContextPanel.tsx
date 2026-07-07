import React, { useMemo } from 'react';
import ContextHub from '@/components/shared/ContextHub';
import type { Project, Chapter } from '@/types';
import { STATE_LABELS } from '@/utils/helpers';

interface ContextPanelProps {
  project: Project;
  chapter?: Chapter;
}

/**
 * 右侧 Context Hub 面板组件
 * 封装 ContextHub，从项目/章节数据中提取上下文信息
 */
const ContextPanel: React.FC<ContextPanelProps> = ({ project, chapter }) => {
  const contextData = useMemo(() => {
    // 从项目数据中提取上下文信息
    const previousChapters: string = chapter
      ? `第 ${chapter.chapter_num} 章 · ${chapter.title || '未命名'} · ${STATE_LABELS[project.current_state]}`
      : '暂无选中章节';

    return {
      characters: project.outline
        ? `从大纲中提取的角色信息：\n${project.outline.slice(0, 200)}${project.outline.length > 200 ? '...' : ''}`
        : '暂未设置大纲，角色信息待提取',
      world: project.world_setting
        ? project.world_setting.slice(0, 300)
        : '暂未设置世界观，设定信息待完善',
      plot: project.outline
        ? `当前阶段：${STATE_LABELS[project.current_state]} · 目标平台：${project.target_platform || '未指定'}`
        : '暂无情节脉络',
      previous: previousChapters,
      emotion: chapter?.summary
        ? `章节摘要：${chapter.summary}`
        : '暂无情感分析数据',
      inspiration: project.meta && typeof project.meta === 'object'
        ? JSON.stringify(project.meta).slice(0, 200)
        : '暂无灵感建议',
      knowledge: `项目：${project.title} · ${STATE_LABELS[project.current_state]} · ${project.current_words.toLocaleString()}字`,
    };
  }, [project, chapter]);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* 头部 */}
      <div className="flex shrink-0 items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-700">
        <h3 className="text-[13px] font-semibold text-gray-700 dark:text-gray-200">
          Context Hub
        </h3>
        <span className="badge badge-neutral text-[11px]">7层上下文</span>
      </div>

      {/* Context Hub 内容 */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <ContextHub contextData={contextData} />
      </div>
    </div>
  );
};

export default ContextPanel;
