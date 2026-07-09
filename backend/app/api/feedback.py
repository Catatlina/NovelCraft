"""反馈信号 API — Phase 8 阅读数据回流"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])

# Phase 8 待实现：
# - 从海外平台回抓阅读量/追读率
# - 章节表现关联分析
# - Prompt 优化建议生成
