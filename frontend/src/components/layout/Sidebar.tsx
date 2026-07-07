import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { NavItem } from '@/components/layout/AppLayout';

interface SidebarProps {
  navItems: NavItem[];
  isActive: (path: string) => boolean;
  userName: string;
  userPlan: string;
}

/**
 * 侧边栏组件
 *
 * 响应式行为：
 * - PC（≥1024px / lg）：完整 240px 侧边栏，显示图标 + 文字
 * - 平板（768-1023px / md-lg）：收窄至 64px，仅显示图标
 * - 移动端（<768px）：通过父组件 hidden 控制
 *
 * 动画：Framer Motion 驱动宽度过渡 + 导航项 Active 状态切换
 */
const Sidebar: React.FC<SidebarProps> = ({ navItems, isActive, userName, userPlan }) => {
  const navigate = useNavigate();

  const handleNavClick = (item: NavItem): void => {
    if (item.disabled) return;
    navigate(item.path);
  };

  return (
    <aside
      className="hidden md:flex md:flex-col md:shrink-0 md:sticky md:top-0 md:h-screen md:border-r md:border-gray-200 md:bg-white dark:md:border-gray-700 dark:md:bg-dark-surface
                 md:w-sidebar-collapsed lg:w-sidebar
                 transition-all duration-200 ease-out z-20"
    >
      {/* Logo 区域 */}
      <div className="flex h-14 shrink-0 items-center gap-3 border-b border-gray-100 px-5 dark:border-gray-700 lg:px-6">
        {/* Logo Mark — 始终可见 */}
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gradient-primary text-sm font-bold text-white">
          星
        </div>
        {/* Logo Text — 仅 PC 可见 */}
        <span className="hidden whitespace-nowrap text-sm font-bold text-gray-800 dark:text-gray-100 lg:block">
          星禾写作助手
        </span>
      </div>

      {/* 导航区域 */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 lg:px-3">
        {/* 分区标签 — 仅 PC 可见 */}
        <span className="hidden px-2 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 lg:block">
          导航
        </span>

        {navItems.map((item: NavItem) => {
          const active: boolean = !item.disabled && isActive(item.path);
          return (
            <button
              key={item.label}
              onClick={() => handleNavClick(item)}
              disabled={item.disabled}
              className={`group relative flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-150 mb-0.5
                lg:px-3 md:justify-center lg:justify-start
                ${
                  item.disabled
                    ? 'text-gray-300 cursor-not-allowed opacity-40 dark:text-gray-600'
                    : active
                      ? 'bg-primary-50 text-primary-500 dark:bg-primary-900/30 dark:text-primary-400'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200'
                }
              `}
              title={item.tooltip || item.label}
            >
              {/* 图标 */}
              <span className={`flex shrink-0 items-center justify-center w-5 h-5 ${active ? 'text-primary-500 dark:text-primary-400' : ''}`}>
                {item.icon}
              </span>

              {/* 文字 — 仅 PC 可见 */}
              <span className="hidden whitespace-nowrap lg:block">{item.label}</span>

              {/* 锁图标（disabled） */}
              {item.disabled && (
                <span className="hidden lg:block ml-auto text-[10px] text-gray-300 dark:text-gray-600">🔒</span>
              )}

              {/* Active Indicator */}
              {active && (
                <motion.div
                  layoutId="sidebar-active-indicator"
                  className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-full bg-primary-500 dark:bg-primary-400 hidden lg:block"
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* 用户区域 — 底部 */}
      <div className="shrink-0 border-t border-gray-100 px-3 py-3 dark:border-gray-700">
        <div className="flex items-center gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer md:justify-center lg:justify-start">
          {/* 头像 */}
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-primary text-xs font-semibold text-white">
            {userName.charAt(0)}
          </div>

          {/* 用户信息 — 仅 PC 可见 */}
          <div className="hidden min-w-0 flex-1 lg:block">
            <p className="truncate text-[13px] font-semibold text-gray-800 dark:text-gray-100">
              {userName}
            </p>
            <p className="truncate text-[11px] text-gray-400 dark:text-gray-500">
              {userPlan}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
