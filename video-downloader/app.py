#!/usr/bin/env python3
"""Scarica Video — scarica video da Instagram e TikTok incollando il link.

Avvio:  python app.py   →  si apre http://localhost:8000
Dipendenze: yt-dlp (pip install -r requirements.txt); ffmpeg consigliato.
"""
import base64
import hmac
import json
import os
import shutil
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse

try:
    import yt_dlp
except ImportError:
    sys.exit("Manca yt-dlp: esegui  pip install -r requirements.txt")

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8000"))
# --telefono: rende l'app raggiungibile dagli altri dispositivi sulla stessa Wi-Fi
HOST = "0.0.0.0" if "--telefono" in sys.argv else os.environ.get("HOST", "127.0.0.1")
# Opzionale, utile per Instagram (post privati o richiesta login):
#   COOKIES_FROM_BROWSER=chrome  (o firefox, safari, edge, brave…)
#   oppure un file cookies.txt (formato Netscape) accanto a app.py
COOKIES_FROM_BROWSER = os.environ.get("COOKIES_FROM_BROWSER", "").strip()
COOKIES_FILE = Path(os.environ.get("COOKIES_FILE", HERE / "cookies.txt"))
# Se impostata, il sito chiede questa password (obbligatoria se l'app è online)
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
MAX_PARALLEL = threading.BoundedSemaphore(int(os.environ.get("MAX_PARALLEL", "3")))

ALLOWED_HOSTS = ("instagram.com", "tiktok.com")
HAS_FFMPEG = shutil.which("ffmpeg") is not None


def platform_of(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower()
    for allowed in ALLOWED_HOSTS:
        if host == allowed or host.endswith("." + allowed):
            return allowed.split(".")[0]
    return None


def ydl_options(outdir: str) -> dict:
    opts = {
        "outtmpl": os.path.join(outdir, "%(uploader|video)s_%(id)s.%(ext)s"),
        "restrictfilenames": True,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cachedir": False,
        "max_filesize": 1024 * 1024 * 1024,  # 1 GB
    }
    if HAS_FFMPEG:
        opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = "b[ext=mp4]/b"
    if COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (COOKIES_FROM_BROWSER,)
    elif COOKIES_FILE.exists():
        opts["cookiefile"] = str(COOKIES_FILE)
    return opts


def friendly_error(msg: str, platform: str) -> str:
    low = msg.lower()
    if platform == "instagram" and any(
        k in low for k in ("login", "cookies", "rate-limit", "private", "not available")
    ):
        return (
            "Instagram richiede l'accesso per questo contenuto. Avvia l'app con "
            "COOKIES_FROM_BROWSER=chrome (o il tuo browser, dove sei loggato) "
            "oppure metti un file cookies.txt nella cartella dell'app."
        )
    if "unsupported url" in low:
        return "Link non supportato: incolla il link di un post, reel o video."
    if "private" in low:
        return "Il video è privato o non disponibile."
    return "Download non riuscito: " + msg.replace("ERROR: ", "").strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "ScaricaVideo/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not APP_PASSWORD:
            return True
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                _, _, pwd = base64.b64decode(header[6:]).decode().partition(":")
            except (ValueError, UnicodeDecodeError):
                return False
            if hmac.compare_digest(pwd.encode(), APP_PASSWORD.encode()):
                return True
        body = b"Password richiesta"
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Scarica Video", charset="UTF-8"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False

    def do_GET(self):
        if not self._authorized():
            return
        if self.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/status":
            self._json(200, {"ffmpeg": HAS_FFMPEG, "yt_dlp": yt_dlp.version.__version__})
        else:
            self._json(404, {"error": "Non trovato"})

    def do_POST(self):
        if not self._authorized():
            return
        if self.path != "/api/download":
            return self._json(404, {"error": "Non trovato"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(min(length, 10_000)) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "Richiesta non valida"})

        url = str(data.get("url", "")).strip()
        platform = platform_of(url)
        if not platform:
            return self._json(400, {"error": "Incolla un link di Instagram o TikTok."})

        if not MAX_PARALLEL.acquire(timeout=60):
            return self._json(503, {"error": "Server occupato, riprova tra poco."})
        tmp = tempfile.mkdtemp(prefix="scarica-")
        try:
            with yt_dlp.YoutubeDL(ydl_options(tmp)) as ydl:
                info = ydl.extract_info(url, download=True)
            files = [p for p in Path(tmp).iterdir() if p.is_file() and not p.name.endswith(".part")]
            if not files:
                return self._json(500, {"error": "Nessun video trovato in questo link (forse è solo una foto)."})
            path = max(files, key=lambda p: p.stat().st_size)
            title = (info or {}).get("title") or path.stem
            size = path.stat().st_size
            mime = "video/mp4" if path.suffix == ".mp4" else "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(size))
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{path.name}\"; filename*=UTF-8''{quote(path.name)}",
            )
            self.send_header("X-Video-Title", quote(title[:200]))
            self.end_headers()
            with path.open("rb") as f:
                shutil.copyfileobj(f, self.wfile, 1024 * 256)
        except yt_dlp.utils.DownloadError as e:
            self._json(422, {"error": friendly_error(str(e), platform)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # noqa: BLE001
            self._json(500, {"error": f"Errore imprevisto: {e}"})
        finally:
            MAX_PARALLEL.release()
            shutil.rmtree(tmp, ignore_errors=True)


def lan_ip() -> str | None:
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # nessun pacchetto inviato
            return s.getsockname()[0]
    except OSError:
        return None


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Scarica Video attivo su {url}  (Ctrl+C per uscire)")
    if HOST != "127.0.0.1" and not APP_PASSWORD:
        print("  ATTENZIONE: app raggiungibile in rete senza password (imposta APP_PASSWORD).")
    if HOST == "0.0.0.0":
        ip = lan_ip()
        if ip:
            print(f"  Dal telefono (stessa Wi-Fi) apri:  http://{ip}:{PORT}")
    if not HAS_FFMPEG:
        print("  Nota: ffmpeg non trovato — alcuni video potrebbero avere qualità più bassa.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nChiuso.")


if __name__ == "__main__":
    main()
