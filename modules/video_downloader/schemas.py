
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
            or not parsed.netloc
        ):
            raise ValueError("La URL del video no es válida.")

        return value


class VideoFormat(BaseModel):
    format_id: str
    extension: Optional[str] = None
    resolution: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None

    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None

    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None

    has_video: bool
    has_audio: bool

    format_note: Optional[str] = None


class VideoInfoResponse(BaseModel):
    title: str
    uploader: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    extractor: Optional[str] = None
    webpage_url: Optional[str] = None
    formats: list[VideoFormat] = Field(default_factory=list)


class VideoDownloadRequest(VideoRequest):
    format_id: str
