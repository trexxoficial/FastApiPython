
from typing import Optional

from pydantic import BaseModel, HttpUrl, Field


class VideoRequest(BaseModel):
    url: HttpUrl


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


class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    format_id: str = Field(
        ...,
        min_length=1,
        description="Identificador del formato de video seleccionado"
    )
