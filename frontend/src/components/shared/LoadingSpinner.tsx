import React from 'react';

interface LoadingSpinnerProps {
  /** 尺寸: sm=24px, md=40px, lg=64px */
  size?: 'sm' | 'md' | 'lg';
  /** 加载提示文本 */
  text?: string;
}

const SIZE_MAP: Record<string, string> = {
  sm: 'h-6 w-6 border-2',
  md: 'h-10 w-10 border-[3px]',
  lg: 'h-16 w-16 border-4',
};

/**
 * 加载动画组件
 * 渐变色旋转圆环 + 可选提示文本
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  text,
}) => {
  const ringClass: string = SIZE_MAP[size] || SIZE_MAP.md;

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div
        className={`animate-spin rounded-full border-primary-200 border-t-primary-500 dark:border-primary-900 dark:border-t-primary-400 ${ringClass}`}
      />
      {text && (
        <span className="text-sm text-gray-400 dark:text-gray-500">{text}</span>
      )}
    </div>
  );
};

export default LoadingSpinner;
