import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import type { QualityDimension } from '@/types';

interface QualityRadarProps {
  /** 各维度得分（0-100） */
  scores: Record<QualityDimension, number>;
}

/** 维度中文标签 */
const DIMENSION_LABELS: Record<QualityDimension, string> = {
  readability: '可读性',
  pacing: '节奏感',
  logic: '逻辑性',
  character: '人物塑造',
  emotion: '情感共鸣',
  style: '文笔风格',
  foreshadow: '伏笔管理',
};

/**
 * 质量雷达图组件
 * 使用 Recharts RadarChart 展示 7 维度的质量评分
 */
const QualityRadar: React.FC<QualityRadarProps> = ({ scores }) => {
  const data = (Object.keys(DIMENSION_LABELS) as QualityDimension[]).map(
    (key: QualityDimension) => ({
      dimension: DIMENSION_LABELS[key],
      score: scores[key] ?? 0,
      fullMark: 100,
    }),
  );

  return (
    <div className="w-full h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <defs>
            <linearGradient id="radarGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#FF6B35" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#FF2442" stopOpacity={0.15} />
            </linearGradient>
          </defs>
          <PolarGrid stroke="#E2E8F0" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 12, fill: '#6B7280' }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#9CA3AF' }}
          />
          <Radar
            name="质量评分"
            dataKey="score"
            stroke="#FF6B35"
            strokeWidth={2}
            fill="url(#radarGradient)"
            fillOpacity={0.6}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default QualityRadar;
