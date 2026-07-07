"""出海发布 API (Phase 6)"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_chapter, get_user_project
from app.db.database import get_db
from app.db.models import NovelChapter, PublishRecord, User

router = APIRouter(prefix="/api/v1/publish", tags=["publish"])


class PublishRequest(BaseModel):
    chapter_id: str
    platform: str


@router.post("/chapter")
async def publish_chapter(req: PublishRequest, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    await get_user_chapter(req.chapter_id, user, db)
    rec = PublishRecord(chapter_id=req.chapter_id, platform=req.platform, status="pending")
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return {"id": str(rec.id), "chapter_id": str(rec.chapter_id), "platform": rec.platform, "status": rec.status}


@router.get("/project/{project_id}")
async def publish_status(project_id: str, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    await get_user_project(project_id, user, db)
    chapters = await db.execute(select(NovelChapter).where(NovelChapter.project_id == project_id))
    chapter_ids = [c.id for c in chapters.scalars().all()]
    if not chapter_ids:
        return {"total_chapters": 0, "platforms": {}, "recent": []}
    records = await db.execute(select(PublishRecord).where(PublishRecord.chapter_id.in_(chapter_ids)))
    recs = records.scalars().all()
    platforms = {}
    for r in recs:
        platforms.setdefault(r.platform, {"published": 0, "pending": 0, "total": len(chapter_ids)})
        platforms[r.platform]["published" if r.status == "published" else "pending"] += 1
    return {"total_chapters": len(chapter_ids), "platforms": platforms,
            "recent": [{"id": str(r.id), "chapter_id": str(r.chapter_id), "platform": r.platform,
                        "status": r.status, "published_url": r.published_url} for r in recs[-20:]]}
