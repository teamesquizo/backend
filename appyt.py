# officialknz/backend/appyt.py
from flask import Flask, request, jsonify, send_file, after_this_request, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import subprocess
import time

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_BIN = os.path.join(BASE_DIR, 'ffmpeg-8.0.1', 'bin')
FFMPEG_EXE = os.path.join(RUTA_BIN, 'ffmpeg.exe')
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'descargas_temp')

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Ruta para servir el HTML principal
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

# Ruta para servir archivos estáticos (JS, CSS, etc.)
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)

@app.route('/api/info', methods=['POST'])
def get_info():
    try:
        url = request.json.get('url')
        ydl_opts = {'quiet': True, 'ffmpeg_location': RUTA_BIN}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'titulo': info.get('title'),
                'duracion': info.get('duration'),
                'thumbnail': info.get('thumbnail')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/descargar', methods=['GET'])
def descargar():
    url = request.args.get('url')
    inicio = float(request.args.get('inicio', 0))
    fin = float(request.args.get('fin', 0))
    
    timestamp = int(time.time())
    archivo_completo = os.path.join(DOWNLOAD_FOLDER, f"input_{timestamp}.mp3")
    archivo_recortado = os.path.join(DOWNLOAD_FOLDER, f"output_{timestamp}.mp3")

    try:
        # 1. Descarga
        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': RUTA_BIN,
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f"input_{timestamp}.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            titulo_real = info.get('title', 'audio_knz')

        # 2. Recorte
        duracion = fin - inicio
        subprocess.run([
            FFMPEG_EXE, '-y', '-ss', str(inicio), '-t', str(duracion),
            '-i', archivo_completo, '-acodec', 'copy', archivo_recortado
        ], check=True)

        # 3. Limpieza del archivo original
        if os.path.exists(archivo_completo): 
            os.remove(archivo_completo)

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(archivo_recortado): 
                    os.remove(archivo_recortado)
            except: 
                pass
            return response

        nombre_archivo = "".join([x for x in titulo_real if x.isalnum() or x in " -_."]).strip() + ".mp3"
        
        # Enviar archivo
        return send_file(
            archivo_recortado,
            as_attachment=True,
            download_name=nombre_archivo,
            mimetype='audio/mpeg'
        )

    except Exception as e:
        # Limpiar en caso de error
        if os.path.exists(archivo_completo): os.remove(archivo_completo)
        if os.path.exists(archivo_recortado): os.remove(archivo_recortado)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Render usa la variable de entorno PORT, si no existe usa el 10000
    port = int(os.environ.get("PORT", 10000))
    # Es VITAL poner host='0.0.0.0' para que sea accesible desde internet
    app.run(host='0.0.0.0', port=port)
