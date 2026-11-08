
import os
import glob
import shutil
import tempfile
import logging
import subprocess
import json

import yt_dlp

from fastapi import HTTPException
from fastapi.responses import FileResponse

from starlette.background import BackgroundTask

from .schemas import VideoDownloadRequest, VideoRequest


# ============================================================
# CONFIGURACIÓN
# ============================================================

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
FFPROBE_LOCATION = shutil.which("ffprobe")


# ============================================================
# CONFIGURACIÓN BASE DE YT-DLP
# ============================================================

def get_base_options():

    options = {
        "quiet": False,
        "no_warnings": False,

        # Runtime JavaScript para YouTube
        "js_runtimes": {
            "deno": {}
        },

        # Componentes EJS
        "remote_components": [
            "ejs:github"
        ],

        # Evitar descargar listas de reproducción
        "noplaylist": True,

        # No ignorar errores
        "ignoreerrors": False,

        # Evitar archivos parciales
        "continuedl": True,
    }

    # Cookies de YouTube
    if os.path.exists(COOKIES_PATH):

        options["cookiefile"] = COOKIES_PATH

        logger.info("Archivo cookies.txt encontrado")

    else:

        logger.warning(
            "No se encontró cookies.txt en: %s",
            COOKIES_PATH
        )

    # FFmpeg
    if FFMPEG_LOCATION:

        options["ffmpeg_location"] = FFMPEG_LOCATION

        logger.info("FFmpeg encontrado: %s", FFMPEG_LOCATION)

    else:

        logger.warning("FFmpeg no fue encontrado")

    return options


# ============================================================
# INFORMACIÓN DEL VIDEO
# ============================================================

def get_video_info_service(request: VideoRequest):

    url = str(request.url)

    ydl_opts = get_base_options()

    ydl_opts.update({
        "skip_download": True,
    })

    try:

        logger.info("Consultando información del video: %s", url)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

            if not info:

                raise Exception(
                    "No se pudo obtener información del video."
                )

            return info

    except Exception as e:

        logger.exception(
            "Error obteniendo información del video"
        )

        raise HTTPException(
            status_code=400,
            detail=f"Error obteniendo información: {str(e)}"
        )


# ============================================================
# SELECTOR DE FORMATOS
# ============================================================

def get_format_selector(format_id: str):

    format_id = format_id.strip()

    # Selección automática de mejor calidad compatible
    if format_id.lower() in ["bv", "best", "auto"]:

        logger.info(
            "Seleccionando automáticamente formato H264 + AAC"
        )

        return (
            "bv*[vcodec^=avc1][ext=mp4]"
            "+ba[acodec^=mp4a][ext=m4a]"
            "/b[ext=mp4][vcodec^=avc1][acodec^=mp4a]"
        )

    # Formato específico solicitado por el usuario.
    # Primero intenta combinarlo con audio AAC.
    # Si no es posible, intenta combinarlo con otro audio.
    # Finalmente, intenta descargar el formato original.
    logger.info("Formato específico solicitado: %s", format_id)

    return (
        f"{format_id}+ba[acodec^=mp4a]"
        f"/{format_id}+ba"
        f"/{format_id}"
    )


# ============================================================
# VALIDAR VIDEO CON FFPROBE
# ============================================================

def validate_video(video_path: str):

    if not FFPROBE_LOCATION:

        raise Exception(
            "FFprobe no está instalado en el servidor."
        )

    command = [
        FFPROBE_LOCATION,
        "-v", "error",
        "-show_entries",
        "format=format_name,duration,size",
        "-show_entries",
        "stream=codec_type,codec_name,width,height",
        "-of", "json",
        video_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    metadata = json.loads(result.stdout)

    streams = metadata.get("streams", [])

    video_stream = next(
        (
            stream for stream in streams
            if stream.get("codec_type") == "video"
        ),
        None
    )

    audio_stream = next(
        (
            stream for stream in streams
            if stream.get("codec_type") == "audio"
        ),
        None
    )

    if not video_stream:

        raise Exception(
            "El archivo no contiene una pista de video válida."
        )

    if not audio_stream:

        raise Exception(
            "El archivo no contiene una pista de audio válida."
        )

    video_codec = video_stream.get("codec_name")
    audio_codec = audio_stream.get("codec_name")

    logger.info("Códec de video: %s", video_codec)
    logger.info("Códec de audio: %s", audio_codec)

    logger.info(
        "Duración: %s segundos",
        metadata.get("format", {}).get("duration")
    )

    logger.info(
        "Resolución: %sx%s",
        video_stream.get("width"),
        video_stream.get("height")
    )

    return {
        "metadata": metadata,
        "video_codec": video_codec,
        "audio_codec": audio_codec
    }


# ============================================================
# CONVERSIÓN A H264 + AAC
# ============================================================

def convert_to_compatible_mp4(video_path: str, temp_dir: str):

    validation = validate_video(video_path)

    video_codec = validation["video_codec"]
    audio_codec = validation["audio_codec"]

    # Si ya es compatible, evitamos recodificar.
    if video_codec == "h264" and audio_codec == "aac":

        logger.info(
            "El video ya utiliza H264 + AAC. No requiere recodificación."
        )

        return video_path

    logger.info(
        "Convirtiendo video a H264 + AAC para mejorar compatibilidad."
    )

    if not FFMPEG_LOCATION:

        raise Exception(
            "FFmpeg es necesario para convertir el video."
        )

    converted_path = os.path.join(
        temp_dir,
        "video_compatible.mp4"
    )

    command = [
        FFMPEG_LOCATION,
        "-y",
        "-i", video_path,

        # Video H264
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        # Audio AAC
        "-c:a", "aac",
        "-b:a", "192k",

        # Compatibilidad con reproducción progresiva
        "-movflags", "+faststart",

        converted_path
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        logger.error(
            "Error FFmpeg: %s",
            result.stderr[-4000:]
        )

        raise Exception(
            "No fue posible convertir el video a H264/AAC."
        )

    if not os.path.exists(converted_path):

        raise Exception(
            "FFmpeg no generó el archivo convertido."
        )

    if os.path.getsize(converted_path) == 0:

        raise Exception(
            "El archivo convertido está vacío."
        )

    # Validar nuevamente el resultado
    final_validation = validate_video(converted_path)

    if (
        final_validation["video_codec"] != "h264"
        or final_validation["audio_codec"] != "aac"
    ):

        raise Exception(
            "La conversión no produjo los códecs esperados."
        )

    logger.info(
        "Conversión completada correctamente: %s bytes",
        os.path.getsize(converted_path)
    )

    return converted_path


# ============================================================
# DESCARGAR VIDEO
# ============================================================

def download_video_service(
    request: VideoDownloadRequest,
    background_tasks
):

    url = str(request.url)

    format_id = request.format_id.strip()

    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp(
        prefix="video_"
    )

    output_template = os.path.join(
        temp_dir,
        "video.%(ext)s"
    )

    format_selector = get_format_selector(format_id)

    ydl_opts = get_base_options()

    ydl_opts.update({

        "format": format_selector,

        "outtmpl": output_template,

        # Contenedor MP4 para combinar audio y video
        "merge_output_format": "mp4",

        # Remux cuando sea necesario
        "postprocessors": [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4",
            }
        ],

    })

    try:

        logger.info("=" * 50)

        logger.info(
            "Iniciando descarga: %s",
            url
        )

        logger.info(
            "Formato solicitado: %s",
            format_selector
        )

        logger.info(
            "Directorio temporal: %s",
            temp_dir
        )

        # Descargar video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download([url])

        # Buscar archivos MP4 generados
        generated_files = glob.glob(
            os.path.join(temp_dir, "*.mp4")
        )

        # Excluir archivos auxiliares
        generated_files = [
            path for path in generated_files
            if not path.endswith("_compatible.mp4")
        ]

        if not generated_files:

            generated_files = glob.glob(
                os.path.join(temp_dir, "video.*")
            )

        if not generated_files:

            logger.error(
                "Archivos encontrados: %s",
                os.listdir(temp_dir)
            )

            raise Exception(
                "No se encontró el archivo generado por yt-dlp."
            )

        # Seleccionar archivo más reciente
        video_path = max(
            generated_files,
            key=os.path.getmtime
        )

        if os.path.getsize(video_path) == 0:

            raise Exception(
                "El archivo descargado está vacío."
            )

        logger.info(
            "Descarga completada: %s bytes",
            os.path.getsize(video_path)
        )

        # Validar y convertir cuando sea necesario
        final_video_path = convert_to_compatible_mp4(
            video_path,
            temp_dir
        )

        # Comprobar archivo final
        if not os.path.exists(final_video_path):

            raise Exception(
                "No se encontró el archivo final."
            )

        logger.info(
            "Video listo para entregar: %s",
            final_video_path
        )

        logger.info("=" * 50)

    except Exception as e:

        # Limpiar archivos en caso de error
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        logger.exception(
            "Error descargando o procesando video"
        )

        if isinstance(e, HTTPException):
            raise

        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el video: {str(e)}"
        )

    # ========================================================
    # LIMPIEZA DESPUÉS DE ENVIAR EL ARCHIVO
    # ========================================================

    def cleanup():

        logger.info(
            "Eliminando archivos temporales: %s",
            temp_dir
        )

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

    return FileResponse(
        path=final_video_path,
        media_type="video/mp4",
        filename="video_descargado.mp4",
        background=BackgroundTask(cleanup)
    )
