
import os
import glob
import shutil
import tempfile
import logging

from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

from fastapi import HTTPException
from fastapi.responses import FileResponse


logger = logging.getLogger(__name__)

COOKIES_PATH = os.getenv(
    "YOUTUBE_COOKIES_PATH",
    "/app/cookies.txt"
)

FFMPEG_PATH = os.getenv("FFMPEG_LOCATION", "/usr/bin")


# ---------------------------------------------------------
# CONFIGURACIÓN BASE
# ---------------------------------------------------------

def get_base_options(use_youtube_cookies: bool = False):
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": False,
        "ffmpeg_location": FFMPEG_PATH,
        "remote_components": ["ejs:github"],
    }

    if use_youtube_cookies:
        if not os.path.isfile(COOKIES_PATH):
            raise HTTPException(
                status_code=401,
                detail={
                    "code": "YOUTUBE_COOKIES_REQUIRED",
                    "message": "YouTube requiere autenticación, pero no hay cookies configuradas."
                }
            )

        options["cookiefile"] = COOKIES_PATH

    return options


# ---------------------------------------------------------
# DETECCIÓN DE PLATAFORMA
# ---------------------------------------------------------

def is_youtube_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()

    return (
        hostname == "youtu.be"
        or hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
        or hostname == "youtube-nocookie.com"
        or hostname.endswith(".youtube-nocookie.com")
    )


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
    ]

    return any(pattern in message for pattern in patterns)


# ---------------------------------------------------------
# EJECUCIÓN INTELIGENTE
# ---------------------------------------------------------

def execute_with_youtube_fallback(url: str, operation):
    """
    Ejecuta primero sin cookies.
    Si YouTube exige autenticación, reintenta con cookies.
    Las demás plataformas se procesan sin cookies de YouTube.
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
                    "message": "Este video requiere iniciar sesión en YouTube. Configura cookies.txt en el servidor."
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
                        "message": "YouTube no aceptó las cookies configuradas. Actualiza cookies.txt e inténtalo nuevamente."
                    }
                )

            raise second_error


# ---------------------------------------------------------
# INFORMACIÓN DEL VIDEO
# ---------------------------------------------------------

def get_video_info_service(request):

    url = str(request.url)

    def operation(use_cookies):

        options = get_base_options(use_cookies)

        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(
                url,
                download=False
            )

    try:
        info, auth_mode = execute_with_youtube_fallback(
            url,
            operation
        )

        if not info:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "VIDEO_UNAVAILABLE",
                    "message": "No fue posible obtener información del video."
                }
            )

        info["auth_mode"] = auth_mode

        return info

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


# ---------------------------------------------------------
# FORMATOS DISPONIBLES
# ---------------------------------------------------------

def get_video_formats_service(request):

    info = get_video_info_service(request)

    return {
        "formats": info.get("formats", []),
        "auth_mode": info.get("auth_mode", "unknown"),
        "extractor": info.get("extractor"),
        "extractor_key": info.get("extractor_key"),
    }


# ---------------------------------------------------------
# DESCARGA DEL VIDEO
# ---------------------------------------------------------

def download_video_service(request):

    url = str(request.url)
    format_id = request.format_id

    temp_dir = tempfile.mkdtemp(prefix="video_download_")

    def perform_download(use_cookies):

        attempt_name = (
            "authenticated" if use_cookies else "anonymous"
        )

        attempt_dir = os.path.join(temp_dir, attempt_name)
        os.makedirs(attempt_dir, exist_ok=True)

        output_template = os.path.join(
            attempt_dir,
            "video.%(ext)s"
        )

        options = get_base_options(use_cookies)

        options.update({
            "format": format_id,
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "postprocessors": [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4"
                }
            ],
        })

        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])

        files = glob.glob(
            os.path.join(attempt_dir, "video.*")
        )

        files = [
            file for file in files
            if not file.endswith((".part", ".ytdl"))
        ]

        if not files:
            raise Exception(
                "yt-dlp no generó el archivo de video."
            )

        # Preferir MP4 si existe
        mp4_files = [
            file for file in files
            if file.lower().endswith(".mp4")
        ]

        candidates = mp4_files if mp4_files else files

        return max(
            candidates,
            key=os.path.getsize
        )

    try:

        video_path, auth_mode = execute_with_youtube_fallback(
            url,
            perform_download
        )

        if not os.path.isfile(video_path):
            raise Exception("El archivo descargado no existe.")

        if os.path.getsize(video_path) == 0:
            raise Exception("El archivo descargado está vacío.")

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
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    except Exception as error:
        logger.exception("Error descargando video")

        shutil.rmtree(temp_dir, ignore_errors=True)

        raise HTTPException(
            status_code=400,
            detail={
                "code": "DOWNLOAD_FAILED",
                "message": str(error)
            }
        )
