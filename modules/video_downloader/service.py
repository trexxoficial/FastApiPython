
import os
import glob
import shutil
import tempfile
import logging
import re

from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video", tags=["Video Downloader"])


# =========================================================
# CONFIGURACIÓN
# =========================================================

COOKIES_PATH = os.getenv(
    "YOUTUBE_COOKIES_PATH",
    "/app/cookies.txt"
)

FFMPEG_PATH = os.getenv(
    "FFMPEG_LOCATION",
    "/usr/bin"
)


# =========================================================
# MODELOS
# =========================================================

class VideoRequest(BaseModel):
    url: str


class VideoDownloadRequest(BaseModel):
    url: str
    format_id: str


# =========================================================
# VALIDACIÓN DE URL
# =========================================================

def validate_video_url(url: str):

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError()

        if not parsed.hostname:
            raise ValueError()

        return url

    except Exception:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_URL",
                "message": "La URL del video no es válida."
            }
        )


# =========================================================
# IDENTIFICACIÓN DE YOUTUBE
# =========================================================

def is_youtube_url(url: str) -> bool:

    hostname = (urlparse(url).hostname or "").lower()

    return (
        hostname == "youtu.be"
        or hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
        or hostname == "youtube-nocookie.com"
        or hostname.endswith(".youtube-nocookie.com")
    )


# =========================================================
# DETECCIÓN DE AUTENTICACIÓN
# =========================================================

def requires_youtube_authentication(error: Exception) -> bool:

    message = str(error).lower()

    patterns = [
        "sign in to confirm",
        "confirm you're not a bot",
        "confirm you’re not a bot",
        "not a bot",
        "login required",
        "authentication required",
        "you must be logged in",
        "requires authentication",
        "cookies are no longer valid",
        "cookies have been rejected",
        "login to view",
        "sign in to view",
    ]

    return any(pattern in message for pattern in patterns)


# =========================================================
# CONFIGURACIÓN YT-DLP
# =========================================================

def get_base_options(use_youtube_cookies: bool = False):

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": False,
        "ffmpeg_location": FFMPEG_PATH,
        "remote_components": ["ejs:github"],
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
    }

    if use_youtube_cookies:

        if not os.path.isfile(COOKIES_PATH):

            raise HTTPException(
                status_code=401,
                detail={
                    "code": "YOUTUBE_COOKIES_REQUIRED",
                    "message": (
                        "YouTube requiere autenticación, "
                        "pero no hay cookies configuradas."
                    )
                }
            )

        options["cookiefile"] = COOKIES_PATH

    return options


# =========================================================
# EJECUCIÓN CON FALLBACK DE COOKIES
# =========================================================

def execute_with_youtube_fallback(url: str, operation):

    """
    1. Intenta primero sin cookies.
    2. Si YouTube exige autenticación, reintenta con cookies.
    3. Las demás plataformas se procesan sin cookies.
    """

    if not is_youtube_url(url):

        return operation(False), "not_applicable"

    try:

        result = operation(False)

        return result, "anonymous"

    except Exception as first_error:

        if not requires_youtube_authentication(first_error):
            raise

        if not os.path.isfile(COOKIES_PATH):

            raise HTTPException(
                status_code=401,
                detail={
                    "code": "YOUTUBE_COOKIES_REQUIRED",
                    "message": (
                        "Este video requiere iniciar sesión en YouTube. "
                        "Configura cookies válidas en el servidor."
                    )
                }
            )

        try:

            result = operation(True)

            return result, "cookies"

        except Exception as second_error:

            if requires_youtube_authentication(second_error):

                raise HTTPException(
                    status_code=401,
                    detail={
                        "code": "YOUTUBE_COOKIES_INVALID",
                        "message": (
                            "YouTube no aceptó las cookies configuradas. "
                            "Actualiza cookies.txt e inténtalo nuevamente."
                        )
                    }
                )

            raise second_error


# =========================================================
# EXTRAER INFORMACIÓN
# =========================================================

def extract_video_info(url: str, use_cookies: bool = False):

    options = get_base_options(use_cookies)

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

    if not info:

        raise HTTPException(
            status_code=404,
            detail={
                "code": "VIDEO_UNAVAILABLE",
                "message": "No fue posible obtener información del video."
            }
        )

    return info


# =========================================================
# INFORMACIÓN DEL VIDEO
# =========================================================

def get_video_info_service(request: VideoRequest):

    url = validate_video_url(request.url)

    try:

        info, auth_mode = execute_with_youtube_fallback(
            url,
            lambda use_cookies: extract_video_info(
                url,
                use_cookies
            )
        )

        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "description": info.get("description"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "extractor": info.get("extractor"),
            "extractor_key": info.get("extractor_key"),
            "auth_mode": auth_mode,
        }

    except HTTPException:
        raise

    except Exception as error:

        logger.exception("Error obteniendo información del video")

        raise HTTPException(
            status_code=400,
            detail={
                "code": "VIDEO_UNAVAILABLE",
                "message": str(error)
            }
        )


# =========================================================
# FORMATOS DISPONIBLES
# =========================================================

def get_video_formats_service(request: VideoRequest):

    url = validate_video_url(request.url)

    try:

        info, auth_mode = execute_with_youtube_fallback(
            url,
            lambda use_cookies: extract_video_info(
                url,
                use_cookies
            )
        )

        formats = []

        for item in info.get("formats", []):

            formats.append({

                "format_id": item.get("format_id"),
                "ext": item.get("ext"),
                "height": item.get("height"),
                "width": item.get("width"),
                "resolution": item.get("resolution"),
                "vcodec": item.get("vcodec"),
                "acodec": item.get("acodec"),
                "filesize": item.get("filesize"),
                "filesize_approx": item.get("filesize_approx"),
                "fps": item.get("fps"),
                "format_note": item.get("format_note"),

            })

        return {
            "formats": formats,
            "auth_mode": auth_mode,
            "extractor": info.get("extractor"),
            "extractor_key": info.get("extractor_key"),
        }

    except HTTPException:
        raise

    except Exception as error:

        logger.exception("Error obteniendo formatos")

        raise HTTPException(
            status_code=400,
            detail={
                "code": "VIDEO_UNAVAILABLE",
                "message": str(error)
            }
        )


# =========================================================
# LIMPIAR NOMBRE DEL ARCHIVO
# =========================================================

def sanitize_filename(filename: str):

    filename = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        filename
    )

    filename = filename.strip()

    return filename[:120] or "video_descargado"


# =========================================================
# DESCARGAR VIDEO
# =========================================================

def download_video_service(request: VideoDownloadRequest):

    url = validate_video_url(request.url)

    format_id = request.format_id.strip()

    if not format_id:

        raise HTTPException(
            status_code=400,
            detail={
                "code": "FORMAT_NOT_AVAILABLE",
                "message": "Debes seleccionar un formato de video."
            }
        )

    temp_dir = tempfile.mkdtemp(
        prefix="video_download_"
    )

    def perform_download(use_cookies: bool):

        attempt_name = (
            "authenticated"
            if use_cookies
            else "anonymous"
        )

        attempt_dir = os.path.join(
            temp_dir,
            attempt_name
        )

        os.makedirs(
            attempt_dir,
            exist_ok=True
        )

        output_template = os.path.join(
            attempt_dir,
            "video.%(ext)s"
        )

        options = get_base_options(use_cookies)

        # ---------------------------------------------
        # CONSULTAR EL FORMATO SELECCIONADO
        # ---------------------------------------------

        with yt_dlp.YoutubeDL(options) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

        available_formats = info.get("formats", [])

        selected_format = next(
            (
                item for item in available_formats
                if str(item.get("format_id")) == format_id
            ),
            None
        )

        if not selected_format:

            raise HTTPException(
                status_code=404,
                detail={
                    "code": "FORMAT_NOT_AVAILABLE",
                    "message": (
                        "El formato seleccionado ya no está disponible. "
                        "Consulta nuevamente los formatos."
                    )
                }
            )

        # ---------------------------------------------
        # COMBINAR VIDEO Y AUDIO
        # ---------------------------------------------

        selected_audio = selected_format.get("acodec")

        if selected_audio == "none":

            # El formato seleccionado solamente contiene video.
            # Se agrega automáticamente la mejor pista de audio.

            format_selector = f"{format_id}+bestaudio"

        else:

            # El formato ya contiene video y audio.

            format_selector = format_id

        # ---------------------------------------------
        # OPCIONES DE DESCARGA
        # ---------------------------------------------

        options.update({

            "format": format_selector,

            "outtmpl": output_template,

            "merge_output_format": "mp4",

            "postprocessors": [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4"
                }
            ],

            "continuedl": False,

            "overwrites": True,

        })

        # ---------------------------------------------
        # EJECUTAR DESCARGA
        # ---------------------------------------------

        with yt_dlp.YoutubeDL(options) as ydl:

            ydl.download([url])

        # ---------------------------------------------
        # LOCALIZAR ARCHIVO GENERADO
        # ---------------------------------------------

        files = glob.glob(
            os.path.join(
                attempt_dir,
                "video.*"
            )
        )

        files = [
            file for file in files
            if not file.endswith((".part", ".ytdl"))
        ]

        if not files:

            raise Exception(
                "yt-dlp no generó el archivo de video."
            )

        # Preferir MP4.

        mp4_files = [
            file for file in files
            if file.lower().endswith(".mp4")
        ]

        candidates = (
            mp4_files
            if mp4_files
            else files
        )

        video_path = max(
            candidates,
            key=os.path.getsize
        )

        if not os.path.isfile(video_path):
            raise Exception("El archivo descargado no existe.")

        if os.path.getsize(video_path) <= 0:
            raise Exception("El archivo descargado está vacío.")

        return video_path

    try:

        video_path, auth_mode = execute_with_youtube_fallback(
            url,
            perform_download
        )

        logger.info(
            "Descarga completada. Modo de autenticación: %s",
            auth_mode
        )

        return {
            "path": video_path,
            "temp_dir": temp_dir,
            "auth_mode": auth_mode,
        }

    except HTTPException:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise

    except Exception as error:

        logger.exception("Error descargando video")

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise HTTPException(
            status_code=400,
            detail={
                "code": "DOWNLOAD_FAILED",
                "message": str(error)
            }
        )


# =========================================================
# ENDPOINT: INFORMACIÓN
# =========================================================

@router.post("/info")
def get_video_info(request: VideoRequest):

    return get_video_info_service(request)


# =========================================================
# ENDPOINT: FORMATOS
# =========================================================

@router.post("/formats")
def get_video_formats(request: VideoRequest):

    return get_video_formats_service(request)


# =========================================================
# ENDPOINT: DESCARGA
# =========================================================

@router.post("/download")
def download_video(request: VideoDownloadRequest):

    result = download_video_service(request)

    video_path = result["path"]

    temp_dir = result["temp_dir"]

    filename = sanitize_filename(
        Path(video_path).stem
    ) + ".mp4"

    # La limpieza se ejecuta después de enviar el archivo.
    cleanup_task = BackgroundTask(
        shutil.rmtree,
        temp_dir,
        ignore_errors=True
    )

    return FileResponse(
        path=video_path,
        filename="video.mp4",
        media_type="video/mp4",
        background=BackgroundTask(
            shutil.rmtree,
            temp_dir,
            ignore_errors=True
        )
    )
