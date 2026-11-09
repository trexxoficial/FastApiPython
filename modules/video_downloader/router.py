
import os
import secrets
import shutil

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
)
from fastapi.responses import FileResponse

from modules.video_downloader.schemas import (
    VideoRequest,
    VideoDownloadRequest,
)

from modules.video_downloader.service import (
    get_video_info_service,
    get_video_formats_service,
    download_video_service,
)


router = APIRouter()


# =====================================================
# VALIDAR CONTRASEÑA
# =====================================================

def verify_access_password(
    x_access_password: str = Header(
        default="",
        alias="X-Access-Password"
    )
):

    configured_password = os.getenv(
        "VIDEO_DOWNLOADER_PASSWORD"
    )

    if not configured_password:

        raise HTTPException(
            status_code=503,
            detail={
                "code": "PASSWORD_NOT_CONFIGURED",
                "message": (
                    "El servicio no tiene configurada "
                    "la contraseña de acceso."
                )
            }
        )

    if not secrets.compare_digest(
        x_access_password,
        configured_password
    ):

        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_ACCESS_PASSWORD",
                "message": "La contraseña ingresada es incorrecta."
            }
        )

    return True


# =====================================================
# CONSULTAR INFORMACIÓN
# =====================================================

@router.post("/info")
def get_video_info(
    request: VideoRequest,
    authorized: bool = Depends(verify_access_password)
):

    return get_video_info_service(request)


# =====================================================
# CONSULTAR FORMATOS
# =====================================================

@router.post("/formats")
def get_video_formats(
    request: VideoRequest,
    authorized: bool = Depends(verify_access_password)
):

    return get_video_formats_service(request)


# =====================================================
# DESCARGAR VIDEO
# =====================================================

@router.post("/download")
def download_video(
    request: VideoDownloadRequest,
    background_tasks: BackgroundTasks,
    authorized: bool = Depends(verify_access_password)
):

    result = download_video_service(request)

    video_path = result["path"]
    temp_dir = result["temp_dir"]
    filename = result.get(
        "filename",
        "video.mp4"
    )

    # Eliminar temporales después de enviar el archivo.
    background_tasks.add_task(
        shutil.rmtree,
        temp_dir,
        ignore_errors=True
    )

    return FileResponse(
        path=video_path,
        filename=filename,
        media_type="video/mp4",
        background=background_tasks
    )
