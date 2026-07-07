import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, TrendingUp, Zap, BookOpen } from 'lucide-react';
import CreateProjectModal from '@/components/CreateProjectModal';

/**
 * 快捷操作面板组件
 * 提供新建项目、扫榜分析、批量生成、拆文学习四个快捷入口
 */
const QuickActions: React.FC = () => {
  const navigate = useNavigate();
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);

  const handleOpenCreate = useCallback(() => {
    setShowCreateModal(true);
  }, []);

  const handleCloseCreate = useCallback(() => {
    setShowCreateModal(false);
  }, []);

  const actions: {
    key: string;
    label: string;
    desc: string;
    icon: React.ReactNode;
    variant: 'primary' | 'secondary';
    onClick: () => void;
  }[] = [
    {
      key: 'new',
      label: '新建项目',
      desc: '从灵感开始',
      icon: <Plus size={20} />,
      variant: 'primary',
      onClick: handleOpenCreate,
    },
    {
      key: 'scan',
      label: '扫榜分析',
      desc: 'AI 推荐方向',
      icon: <TrendingUp size={20} />,
      variant: 'secondary',
      onClick: () => navigate('/trends'),
    },
    {
      key: 'batch',
      label: '批量生成',
      desc: '多章节流水线',
      icon: <Zap size={20} />,
      variant: 'secondary',
      onClick: () => navigate('/'),
    },
    {
      key: 'analyze',
      label: '拆文学习',
      desc: '爆款小说拆解',
      icon: <BookOpen size={20} />,
      variant: 'secondary',
      onClick: () => navigate('/trends'),
    },
  ];

  return (
    <>
      <section className="card">
        <div className="mb-4 border-b border-gray-100 pb-4 dark:border-gray-700">
          <h3 className="text-[16px] font-semibold text-gray-800 dark:text-gray-100">
            快捷操作
          </h3>
        </div>

        <div className="flex flex-col gap-3">
          {actions.map((action) => (
            <button
              key={action.key}
              onClick={action.onClick}
              className={
                action.variant === 'primary'
                  ? 'btn-primary btn-lg !justify-start !px-5'
                  : 'btn-secondary btn-lg !justify-start !px-5'
              }
            >
              <span className="flex h-8 w-8 items-center justify-center">
                {action.icon}
              </span>
              <span>{action.label}</span>
              <span className="ml-auto text-[12px] opacity-70">
                {action.desc}
              </span>
            </button>
          ))}
        </div>
      </section>

      <CreateProjectModal open={showCreateModal} onClose={handleCloseCreate} />
    </>
  );
};

export default QuickActions;
