# service.py
import os
import sys
import tempfile
import subprocess
import logging
from fastapi.responses import FileResponse
from fastapi import HTTPException
import yt_dlp

# Calcula la ruta absoluta hacia la raíz del proyecto donde está cookies.txt
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.txt")

# 1. Detección automática del entorno (Railway = Linux, Local = Windows)
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_STATIC_URL"):
    FFMPEG_LOCATION = "ffmpeg"
else:
    FFMPEG_LOCATION = "ffmpeg.exe" # En local asume que está en la raíz junto a main.py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_downloader")

from .schemas import VideoDownloadRequest, VideoRequest

def get_video_info_service(request: VideoRequest):
    """Obtiene información y formatos del video"""
    url = str(request.url)
    ydl_opts = {
        "quiet": True, 
        "no_warnings": True,
        "cookiefile": COOKIES_PATH,
        "extractor_args": {"youtube": {"client": ["android", "ios"]}},
        "ignore_no_formats_error": True  
    }
    
    if FFMPEG_LOCATION != "ffmpeg":
        ydl_opts["ffmpeg_location"] = FFMPEG_LOCATION

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"Error al obtener info del video: {e}")
        raise HTTPException(status_code=400, detail=f"Error al obtener la información: {str(e)}")



def download_video_service(request: VideoDownloadRequest, background_tasks):
    url_str = str(request.url)
    
    # Crea un archivo temporal seguro
    fd, temp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd) 
    
    # 2. Comando yt-dlp usando la variable dinámica de FFMPEG
    command = [
        sys.executable, "-m", "yt_dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "--no-playlist",
        "--cookies", "cookies.txt",
        "--ffmpeg-location", FFMPEG_LOCATION, # Inyecta la ruta según el SO
        "-f", f"{request.format_id}+ba/{request.format_id}/b",
        "--merge-output-format", "mp4",
        "-o", temp_path,
        url_str
    ]

    try:
        subprocess.run(command, check=True)
        
        # Validación crítica
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise Exception("yt-dlp generó un archivo vacío (posible bloqueo de YouTube).")
            
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Error descargando video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el video: {str(e)}")

    print(f"Éxito: Archivo temporal de video generado en: {temp_path}")

    # Limpieza segura
    def cleanup_file(path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Limpieza: Archivo temporal {path} eliminado.")
        except Exception as e:
            logger.error(f"Error al intentar borrar el archivo temporal: {e}")

    # Programar borrado automático tras enviar la respuesta
    background_tasks.add_task(cleanup_file, temp_path)

    # FileResponse con cabeceras estrictas
    return FileResponse(
        path=temp_path,
        media_type="video/mp4",
        filename="video_descargado.mp4",
        headers={"Content-Disposition": 'attachment; filename="video_descargado.mp4"'}
    )