import React from 'react';
import { ChevronDown, BookOpen, Users, Map, Swords, Heart, Lightbulb, Search } from 'lucide-react';

/** 上下文数据层定义 */
interface ContextLayer {
  id: string;
  label: string;
  icon: React.ReactNode;
  content: string;
  badge?: number;
}

interface ContextData {
  characters?: string;
  world?: string;
  plot?: string;
  previous?: string;
  emotion?: string;
  inspiration?: string;
  knowledge?: string;
}

interface ContextHubProps {
  contextData: ContextData;
}

/**
 * 上下文中枢组件
 * 展示 7 层创作上下文信息卡片（角色/世界观/情节/前情/情感/灵感/知识），可折叠
 */
const ContextHub: React.FC<ContextHubProps> = ({ contextData }) => {
  const [collapsed, setCollapsed] = React.useState<Set<string>>(new Set());

  const toggle = (id: string): void => {
    setCollapsed((prev: Set<string>) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const layers: ContextLayer[] = [
    {
      id: 'characters',
      label: '角色档案',
      icon: <Users size={16} />,
      content: contextData.characters || '暂无角色信息',
    },
    {
      id: 'world',
      label: '世界观',
      icon: <Map size={16} />,
      content: contextData.world || '暂无世界观设定',
    },
    {
      id: 'plot',
      label: '情节脉络',
      icon: <BookOpen size={16} />,
      content: contextData.plot || '暂无情节信息',
    },
    {
      id: 'previous',
      label: '前情提要',
      icon: <Swords size={16} />,
      content: contextData.previous || '暂无前置章节',
    },
    {
      id: 'emotion',
      label: '情感曲线',
      icon: <Heart size={16} />,
      content: contextData.emotion || '暂无情感分析',
    },
    {
      id: 'inspiration',
      label: '灵感火花',
      icon: <Lightbulb size={16} />,
      content: contextData.inspiration || '暂无灵感建议',
    },
    {
      id: 'knowledge',
      label: '知识检索',
      icon: <Search size={16} />,
      content: contextData.knowledge || '暂无知识库结果',
    },
  ];

  return (
    <div className="flex flex-col">
      {layers.map((layer: ContextLayer) => {
        const isCollapsed: boolean = collapsed.has(layer.id);
        return (
          <div
            key={layer.id}
            className={`border-b border-gray-100 dark:border-gray-700 ${
              isCollapsed ? '' : ''
            }`}
          >
            {/* 面板标题 */}
            <button
              onClick={() => toggle(layer.id)}
              className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <span className="flex items-center gap-2 text-[13px] font-semibold text-gray-700 dark:text-gray-200">
                <span className="text-gray-400 dark:text-gray-500">
                  {layer.icon}
                </span>
                {layer.label}
                {layer.badge !== undefined && layer.badge > 0 && (
                  <span className="badge badge-primary ml-1 text-[11px]">
                    {layer.badge}
                  </span>
                )}
              </span>
              <ChevronDown
                size={14}
                className={`text-gray-400 transition-transform duration-150 ${
                  isCollapsed ? '-rotate-90' : ''
                }`}
              />
            </button>

            {/* 面板内容 */}
            {!isCollapsed && (
              <div className="px-4 pb-3 text-[13px] leading-relaxed text-gray-500 dark:text-gray-400">
                {layer.content}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ContextHub;
