from fastapi import APIRouter, BackgroundTasks
from .schemas import VideoRequest, VideoDownloadRequest
from .service import get_video_info_service, download_video_service

router = APIRouter(
    prefix="/api/video",
    tags=["Video Downloader"]
)

@router.post("/info")
async def get_video_info(request: VideoRequest):
    return get_video_info_service(request)

@router.post("/formats")
async def get_video_formats(request: VideoRequest):
    info = get_video_info_service(request)
    return {"formats": info.get("formats", [])}

@router.post("/download")
async def download_video(request: VideoDownloadRequest, background_tasks: BackgroundTasks):
    # Pasamos background_tasks al servicio para que pueda programar el borrado
    return download_video_service(request, background_tasks)