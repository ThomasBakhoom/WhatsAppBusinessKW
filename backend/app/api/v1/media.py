"""Media upload/download API."""

from uuid import UUID, uuid4
from fastapi import APIRouter, File, UploadFile
from app.dependencies import AuthUser, TenantDbSession
from app.core.storage import StorageService
from app.schemas.common import CamelModel

router = APIRouter()


class MediaResponse(CamelModel):
    url: str
    filename: str
    content_type: str
    size: int


@router.post("/upload", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    db: TenantDbSession = None,
    user: AuthUser = None,
):
    """Upload a media file (image, video, audio, document)."""
    contents = await file.read()
    ext = (file.filename or "file").split(".")[-1]
    key = f"media/{user.company_id}/{uuid4().hex}.{ext}"

    storage = StorageService()
    url = await storage.upload(key, contents, content_type=file.content_type or "application/octet-stream")

    return MediaResponse(
        url=url, filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size=len(contents),
    )


@router.get("/{media_id}")
async def get_media_url(media_id: str, db: TenantDbSession = None, user: AuthUser = None):
    """Get a presigned URL for a media file."""
    storage = StorageService()
    url = await storage.get_presigned_url(f"media/{user.company_id}/{media_id}")
    return {"url": url}
