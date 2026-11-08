
import os
import shutil
import tempfile
import logging

import yt_dlp

from fastapi import HTTPException
from fastapi.responses import FileResponse

from .schemas import VideoDownloadRequest, VideoRequest


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("video_downloader")


# Directorio raíz del proyecto
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

COOKIES_PATH = os.path.join(BASE_DIR, "cookies.txt")

FFMPEG_LOCATION = shutil.which("ffmpeg")


def get_base_options():

    options = {
        "quiet": False,
        "no_warnings": False,

        # Solucionador JavaScript
        "js_runtimes": {
            "deno": {}
        },

        # Componentes EJS
        "remote_components": ["ejs:github"],

        # No descargar listas completas
        "noplaylist": True,

        # Evitar formatos incompletos
        "ignoreerrors": False,
    }

    # Cookies opcionales
    if os.path.exists(COOKIES_PATH):
        options["cookiefile"] = COOKIES_PATH
        logger.info("Archivo cookies.txt encontrado")

    # FFmpeg
    if FFMPEG_LOCATION:
        options["ffmpeg_location"] = FFMPEG_LOCATION
    else:
        logger.warning("FFmpeg no fue encontrado")

    return options


def get_video_info_service(request: VideoRequest):

    url = str(request.url)

    ydl_opts = get_base_options()

    ydl_opts.update({
        "skip_download": True,
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

            return info

    except Exception as e:

        logger.exception("Error obteniendo información del video")

        raise HTTPException(
            status_code=400,
            detail=f"Error obteniendo información: {str(e)}"
        )


def download_video_service(request: VideoDownloadRequest, background_tasks):

    url = str(request.url)

    format_id = request.format_id.strip()

    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp(prefix="video_")

    output_template = os.path.join(
        temp_dir,
        "video.%(ext)s"
    )

    # Selector de formato
    if format_id.lower() in ["bv", "best", "auto"]:

        format_selector = "bv*+ba/b"

    else:

        # Combinar el formato seleccionado con el mejor audio disponible
        format_selector = f"{format_id}+bestaudio/best"

    ydl_opts = get_base_options()

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        "merge_output_format": "mp4",

        "postprocessors": [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4",
            }
        ],

    })

    try:

        logger.info(f"Iniciando descarga: {url}")
        logger.info(f"Formato solicitado: {format_selector}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download([url])

        # Buscar archivo generado
        video_path = os.path.join(temp_dir, "video.mp4")

        if not os.path.exists(video_path):

            archivos = os.listdir(temp_dir)

            logger.info(f"Archivos generados: {archivos}")

            raise Exception(
                "No se encontró el archivo MP4 después de la descarga."
            )

        if os.path.getsize(video_path) == 0:

            raise Exception("El archivo generado está vacío.")

        logger.info(
            f"Descarga exitosa: {os.path.getsize(video_path)} bytes"
        )

    except Exception as e:

        shutil.rmtree(temp_dir, ignore_errors=True)

        logger.exception("Error descargando video")

        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el video: {str(e)}"
        )

    # Eliminar archivos después de enviar la respuesta
    def cleanup():
        shutil.rmtree(temp_dir, ignore_errors=True)

    background_tasks.add_task(cleanup)

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename="video_descargado.mp4",
        background=background_tasks
    )
