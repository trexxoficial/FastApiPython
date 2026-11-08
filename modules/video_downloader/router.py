
import os
import shutil

from fastapi import APIRouter, BackgroundTasks

from modules.video_downloader.schemas import (
    VideoRequest,
    VideoDownloadRequest,
)

from modules.video_downloader.service import (
    get_video_info_service,
    get_video_formats_service,
    download_video_service,
)

from fastapi.responses import FileResponse


router = APIRouter()


@router.post("/info")
def get_video_info(request: VideoRequest):
    return get_video_info_service(request)


@router.post("/formats")
def get_video_formats(request: VideoRequest):
    return get_video_formats_service(request)


@router.post("/download")
def download_video(
    request: VideoDownloadRequest,
    background_tasks: BackgroundTasks
):
    result = download_video_service(request)

    video_path = result["path"]
    temp_dir = result["temp_dir"]

    background_tasks.add_task(
        shutil.rmtree,
        temp_dir,
        ignore_errors=True
    )

    filename = os.path.basename(video_path)

    return FileResponse(
        path=video_path,
        filename=filename,
        media_type="video/mp4"
    )
