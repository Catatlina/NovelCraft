"""伏笔系统 Phase 3 补全 — Payoff 质量检测 + 超期自动标记"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import ForeshadowPool, NovelChapter, User
from app.services.deepseek_client import DeepSeekError, chat_completion

router = APIRouter(prefix="/api/v1/foreshadows", tags=["foreshadows"])


class PayoffCheckRequest(BaseModel):
    foreshadow_id: str
    chapter_content: str


PAYOFF_DETECTION_PROMPT = """评估以下伏笔回收的质量。

## 原始伏笔
{foreshadow_description}
埋于第{planted_chapter}章，预期回收范围：{expected_range}

## 回收章节内容
{chapter_content}

## 评估标准
1. 回收内容是否与埋点预期一致？(consistency: 1-10)
2. 回收是否有足够的戏剧性？不是"顺便提一句"就完了 (drama: 1-10)
3. 回收后是否推进了剧情或揭示了新信息？(impact: 1-10)
4. 是否存在"水过"嫌疑——回收得太随意、太敷衍？(watered_down: true/false)

## 输出 JSON
{{"consistency": 8, "drama": 7, "impact": 6, "watered_down": false, "overall_quality": "good/passable/weak",
 "note": "一句话评价", "payoff_quality_score": 7.0}}"""


OVERDUE_CHECK_PROMPT = """检查以下伏笔是否已超期，并判断是否已隐式回收。

## 伏笔
{description}
埋于第{planted}章，预期在{expected}章前回收。
当前已写到第{current_chapter}章。

## 判断标准
- 如果当前章节数已远超过预期回收范围（超过5章以上），标记为 overdue
- 如果在近期章节中能找到隐式回收的证据（读者能感受到伏笔已自然解开），标记为 implicitly_paid_off
- 否则标记为 overdue

输出 JSON: {{"status": "overdue/implicitly_paid_off/still_active", "note": "判断依据"}}"""


@router.post("/{foreshadow_id}/check-payoff")
async def check_payoff_quality(
    foreshadow_id: str,
    req: PayoffCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """检测伏笔回收质量（Payoff 检测）"""
    fs = await db.get(ForeshadowPool, foreshadow_id)
    if not fs:
        raise HTTPException(404, "伏笔不存在")
    await get_user_project(str(fs.project_id), user, db)
    if fs.status != "paid_off":
        raise HTTPException(400, "伏笔尚未标记为已回收，无法检测 Payoff 质量")

    prompt = (PAYOFF_DETECTION_PROMPT
        .replace("{foreshadow_description}", fs.description or "")
        .replace("{planted_chapter}", str(fs.planted_chapter))
        .replace("{expected_range}", fs.expected_payoff_range or "未指定")
        .replace("{chapter_content}", req.chapter_content[:3000]))
    try:
        r = await chat_completion([{"role": "user", "content": prompt}], temperature=0.3)
        raw = r["content"].strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        data = json.loads(raw)
    except (DeepSeekError, json.JSONDecodeError):
        raise HTTPException(502, "AI Payoff 检测服务暂时不可用")

    fs.payoff_quality_note = json.dumps(data, ensure_ascii=False)
    await db.commit()
    return {"foreshadow_id": foreshadow_id, "payoff_quality": data}


@router.post("/auto-check-overdue")
async def auto_check_overdue(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """自动检测超期伏笔（批量）"""
    await get_user_project(project_id, user, db)
    all_fs = await db.execute(
        select(ForeshadowPool).where(
            ForeshadowPool.project_id == project_id,
            ForeshadowPool.status == "planted",
        )
    )
    planted = all_fs.scalars().all()
    if not planted:
        return {"checked": 0, "overdue": 0}

    # Get current chapter count
    ch_count = await db.execute(
        select(NovelChapter.chapter_num)
        .where(NovelChapter.project_id == project_id)
        .order_by(NovelChapter.chapter_num.desc())
        .limit(1)
    )
    current = (ch_count.scalar() or 0)

    overdue_count = 0
    for fs in planted:
        # Parse expected range like "10-20章" or "ch45-50"
        expected_max = fs.planted_chapter + 5  # default: 5 chapters grace
        if fs.expected_payoff_range:
            import re
            nums = re.findall(r'\d+', fs.expected_payoff_range)
            if len(nums) >= 2:
                expected_max = int(nums[1])
            elif len(nums) == 1:
                expected_max = int(nums[0])

        if current > expected_max + 5:  # 5 chapters grace period
            fs.status = "overdue"
            overdue_count += 1

    await db.commit()
    return {"checked": len(planted), "overdue": overdue_count, "current_chapter": current}


# ═══ Base foreshadow endpoints (list, stats, mark-overdue) ═══

class ForeshadowOut(BaseModel):
    id: str
    project_id: str
    description: str
    planted_chapter: int
    expected_payoff_range: str | None
    status: str
    payoff_chapter: int | None
    payoff_quality_note: str | None
    model_config = {"from_attributes": True}


@router.get("/project/{project_id}", response_model=list[ForeshadowOut])
async def list_foreshadows(project_id: str, status: str | None = None,
                           db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await get_user_project(project_id, user, db)
    q = select(ForeshadowPool).where(ForeshadowPool.project_id == project_id)
    if status: q = q.where(ForeshadowPool.status == status)
    q = q.order_by(ForeshadowPool.planted_chapter)
    result = await db.execute(q)
    return [ForeshadowOut(id=str(f.id), project_id=str(f.project_id), description=f.description,
            planted_chapter=f.planted_chapter, expected_payoff_range=f.expected_payoff_range,
            status=f.status, payoff_chapter=f.payoff_chapter, payoff_quality_note=f.payoff_quality_note)
            for f in result.scalars().all()]


@router.get("/stats/{project_id}")
async def foreshadow_stats(project_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await get_user_project(project_id, user, db)
    result = await db.execute(select(ForeshadowPool).where(ForeshadowPool.project_id == project_id))
    all_fs = result.scalars().all()
    planted = sum(1 for f in all_fs if f.status == "planted")
    paid_off = sum(1 for f in all_fs if f.status == "paid_off")
    overdue = sum(1 for f in all_fs if f.status == "overdue")
    resolved = [f for f in all_fs if f.status == "paid_off" and f.payoff_chapter and f.planted_chapter]
    avg_cycle = sum(f.payoff_chapter - f.planted_chapter for f in resolved) / len(resolved) if resolved else 0
    return {"total": len(all_fs), "planted": planted, "paid_off": paid_off, "overdue": overdue,
            "recovery_rate": round(paid_off/len(all_fs)*100,1) if all_fs else 0, "avg_recovery_chapters": round(avg_cycle,1)}


@router.post("/{foreshadow_id}/mark-overdue")
async def mark_overdue(foreshadow_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    f = await db.get(ForeshadowPool, foreshadow_id)
    if not f: raise HTTPException(404, "伏笔不存在")
    await get_user_project(str(f.project_id), user, db)
    f.status = "overdue"
    await db.commit()
    return {"status": "overdue"}
