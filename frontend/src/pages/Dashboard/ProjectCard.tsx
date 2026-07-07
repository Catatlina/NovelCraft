import React from 'react';
import { motion } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import type { Project } from '@/types';
import { STATE_LABELS, STATE_COLORS, fmtWords } from '@/utils/helpers';

interface ProjectCardProps {
  project: Project;
  onSelect: (id: string) => void;
}

/** 状态对应的进度百分比估算 */
const STATE_PROGRESS: Record<string, number> = {
  idea: 10,
  outline: 25,
  world: 40,
  writing: 65,
  review: 85,
  publish: 100,
};

/**
 * 项目卡片组件
 * 展示项目标题、状态、进度和字数，点击跳转到创作工作台
 */
const ProjectCard: React.FC<ProjectCardProps> = ({ project, onSelect }) => {
  const stateColor: string = STATE_COLORS[project.current_state] || '#9CA3AF';
  const progress: number = STATE_PROGRESS[project.current_state] || 0;
  const targetWords: number = project.target_words || 0;

  return (
    <motion.div
      className="card-interactive card cursor-pointer overflow-hidden !p-0"
      onClick={() => onSelect(project.id)}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.15 }}
    >
      {/* 渐变色头部 */}
      <div
        className="flex items-center gap-3 px-5 py-3"
        style={{
          background: `linear-gradient(135deg, ${stateColor}15 0%, ${stateColor}05 100%)`,
          borderBottom: `1px solid ${stateColor}20`,
        }}
      >
        {/* 书名首字图标 */}
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-lg font-bold text-white"
          style={{ background: `linear-gradient(135deg, ${stateColor}, ${stateColor}cc)` }}
        >
          {project.title.charAt(0)}
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="truncate text-[15px] font-semibold text-gray-800 dark:text-gray-100">
            {project.title}
          </h4>
          <div className="mt-0.5 flex items-center gap-2">
            <span
              className="badge text-[11px]"
              style={{
                backgroundColor: `${stateColor}15`,
                color: stateColor,
              }}
            >
              {STATE_LABELS[project.current_state]}
            </span>
            {project.target_platform && (
              <span className="text-[12px] text-gray-400 dark:text-gray-500">
                {project.target_platform}
              </span>
            )}
          </div>
        </div>
        <ChevronRight size={18} className="shrink-0 text-gray-300 dark:text-gray-600" />
      </div>

      {/* 卡片内容 */}
      <div className="px-5 py-4">
        {/* 进度条 */}
        <div className="mb-3 flex items-center gap-3">
          <span className="text-[11px] text-gray-400 dark:text-gray-500">进度</span>
          <div className="progress flex-1">
            <div
              className="progress-bar"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="font-mono text-[12px] font-semibold text-gray-600 dark:text-gray-300">
            {progress}%
          </span>
        </div>

        {/* 数据行 */}
        <div className="flex gap-6">
          <div>
            <span className="text-[12px] text-gray-400 dark:text-gray-500">已写</span>
            <p className="font-mono text-[14px] font-semibold text-gray-700 dark:text-gray-200">
              {fmtWords(project.current_words || 0)}
            </p>
          </div>
          <div>
            <span className="text-[12px] text-gray-400 dark:text-gray-500">目标</span>
            <p className="font-mono text-[14px] font-semibold text-gray-700 dark:text-gray-200">
              {targetWords > 0 ? fmtWords(targetWords) : '—'}
            </p>
          </div>
          <div>
            <span className="text-[12px] text-gray-400 dark:text-gray-500">创建</span>
            <p className="text-[14px] font-medium text-gray-500 dark:text-gray-400">
              {project.created_at
                ? new Date(project.created_at).toLocaleDateString('zh-CN', {
                    month: 'short',
                    day: 'numeric',
                  })
                : '—'}
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ProjectCard;
