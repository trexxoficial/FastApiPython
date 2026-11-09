
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, validator


class VideoRequest(BaseModel):
    url: str

    @validator("url")
    def validate_url(cls, value):
        value = value.strip()
        parsed = urlparse(value)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
        ):
            raise ValueError("La URL del video no es válida.")

        return value


class VideoDownloadRequest(VideoRequest):
    format_id: str

    @validator("format_id")
    def validate_format_id(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Debes seleccionar un formato.")

        return value


class VideoFormat(BaseModel):
    format_id: str
    ext: Optional[str] = None
    resolution: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    format_note: Optional[str] = None


class VideoInfoResponse(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    uploader: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    extractor: Optional[str] = None
    extractor_key: Optional[str] = None
    webpage_url: Optional[str] = None
    auth_mode: Optional[str] = None
    formats: list[VideoFormat] = Field(default_factory=list)
