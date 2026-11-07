import os
import sys
import tempfile
import subprocess
import logging
from fastapi.responses import FileResponse
from fastapi import HTTPException
import yt_dlp


FFMPEG_LOCATION = "./ffmpeg.exe"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_downloader")

from .schemas import VideoDownloadRequest, VideoRequest

def get_video_info_service(request: VideoRequest):
    """Obtiene información y formatos del video"""
    url = str(request.url)
    ydl_opts = {"quiet": True, "no_warnings": True}
    if FFMPEG_LOCATION and FFMPEG_LOCATION != "ffmpeg":
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
    
    # 1. Crea un archivo temporal seguro
    fd, temp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd) 
    
    # 2. Comando yt-dlp con motor JS y componentes remotos
    command = [
        sys.executable, "-m", "yt_dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "--no-playlist",  # Bloquea la descarga de listas de reproducción completas
        "--ffmpeg-location", "./ffmpeg.exe", # Apunta al archivo local que descargaremos
        "-f", f"{request.format_id}+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", temp_path,
        url_str
    ]

    try:
        subprocess.run(command, check=True)
        
        # Validación crítica: Verificar que yt-dlp no haya fallado silenciosamente dejando un archivo vacío
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise Exception("yt-dlp generó un archivo vacío (posible bloqueo de YouTube).")
            
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Error descargando video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el video: {str(e)}")

    print(f"Éxito: Archivo temporal de video generado en: {temp_path}")

    # 3. Limpieza segura
    def cleanup_file(path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Limpieza: Archivo temporal {path} eliminado.")
        except Exception as e:
            logger.error(f"Error al intentar borrar el archivo temporal: {e}")

    # 4. Programar borrado automático tras enviar la respuesta
    background_tasks.add_task(cleanup_file, temp_path)

    # 5. FileResponse con cabeceras estrictas para forzar la descarga en clientes HTTP
    return FileResponse(
        path=temp_path,
        media_type="video/mp4",
        filename="video_descargado.mp4",
        headers={"Content-Disposition": 'attachment; filename="video_descargado.mp4"'}
    )