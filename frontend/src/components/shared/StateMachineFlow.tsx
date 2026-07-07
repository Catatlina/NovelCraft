import React from 'react';
import { motion } from 'framer-motion';
import type { ProjectState } from '@/types';
import { STATE_LABELS } from '@/utils/helpers';

interface StateMachineFlowProps {
  currentState: ProjectState;
  onTransition?: (newState: ProjectState) => void;
}

/** 状态顺序 */
const STATE_ORDER: ProjectState[] = [
  'idea',
  'outline',
  'world',
  'writing',
  'review',
  'publish',
];

/**
 * 状态机流程图组件
 * 展示 6 阶段写作流程，当前阶段高亮脉冲动画，点击可触发状态迁移
 */
const StateMachineFlow: React.FC<StateMachineFlowProps> = ({
  currentState,
  onTransition,
}) => {
  const currentIdx: number = STATE_ORDER.indexOf(currentState);

  return (
    <div className="flex items-center justify-center gap-0 overflow-x-auto py-6 px-2">
      {STATE_ORDER.map((state: ProjectState, idx: number) => {
        const isDone: boolean = idx < currentIdx;
        const isCurrent: boolean = idx === currentIdx;
        const isFuture: boolean = idx > currentIdx;

        return (
          <React.Fragment key={state}>
            {/* 状态节点 */}
            <motion.button
              className={`relative z-10 flex flex-col items-center gap-1.5 shrink-0 ${
                onTransition && isFuture ? 'cursor-pointer' : 'cursor-default'
              }`}
              onClick={() => {
                if (onTransition && isFuture) {
                  onTransition(state);
                }
              }}
              whileHover={isFuture && onTransition ? { scale: 1.05 } : undefined}
              whileTap={isFuture && onTransition ? { scale: 0.95 } : undefined}
            >
              {/* 圆形图标 */}
              <motion.div
                className={`flex h-14 w-14 items-center justify-center rounded-full border-[3px] text-[13px] font-bold transition-colors duration-300 ${
                  isCurrent
                    ? 'border-transparent bg-gradient-primary text-white shadow-primary'
                    : isDone
                      ? 'border-gray-300 bg-white text-gray-400 opacity-60 dark:border-gray-600 dark:bg-gray-800'
                      : 'border-gray-200 bg-white text-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-500'
                }`}
                animate={
                  isCurrent
                    ? {
                        boxShadow: [
                          '0 0 0 0 rgba(255,107,53,0.4)',
                          '0 0 0 8px rgba(255,107,53,0)',
                        ],
                      }
                    : {}
                }
                transition={
                  isCurrent
                    ? { repeat: Infinity, duration: 2, ease: 'easeOut' }
                    : {}
                }
              >
                {isDone ? '✓' : idx + 1}
              </motion.div>

              {/* 状态标签 */}
              <span
                className={`text-[13px] font-medium whitespace-nowrap ${
                  isCurrent
                    ? 'text-primary-500 dark:text-primary-400'
                    : isDone
                      ? 'text-gray-400 dark:text-gray-500'
                      : 'text-gray-400 dark:text-gray-500'
                }`}
              >
                {STATE_LABELS[state] || state}
              </span>
            </motion.button>

            {/* 连接线 */}
            {idx < STATE_ORDER.length - 1 && (
              <div
                className={`mx-0.5 mb-10 h-[3px] w-8 shrink-0 rounded-full sm:w-12 ${
                  idx < currentIdx
                    ? 'bg-primary-400 dark:bg-primary-600'
                    : 'bg-gray-200 dark:bg-gray-700'
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default StateMachineFlow;
