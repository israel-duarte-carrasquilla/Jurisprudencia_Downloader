import sys
import os

# Asegurar que la raíz del proyecto esté en el PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configurar entorno
os.environ.setdefault("STORAGE_MODE", "local")

try:
    from a2wsgi import ASGIMiddleware
    from main import api_app
    
    # Exponer 'application' como WSGI compatible con Phusion Passenger de cPanel
    application = ASGIMiddleware(api_app)
except Exception as e:
    def application(environ, start_response):
        status = '200 OK'
        output = f"""
        <html>
        <head><title>Jurisprudencia Downloader - Estado</title></head>
        <body style="font-family: sans-serif; padding: 40px; line-height: 1.6;">
            <h2>Jurisprudencia Downloader</h2>
            <p>La aplicación está iniciando en cPanel.</p>
            <p><strong>Aviso de inicialización:</strong> {e}</p>
            <p>Asegúrese de instalar las dependencias ejecutando en la terminal de cPanel:</p>
            <pre style="background: #f4f4f4; padding: 10px; border-radius: 5px;">pip install -r requirements.txt</pre>
        </body>
        </html>
        """.encode('utf-8')
        response_headers = [('Content-type', 'text/html; charset=utf-8'),
                            ('Content-Length', str(len(output)))]
        start_response(status, response_headers)
        return [output]
