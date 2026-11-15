# Scarica Video — Instagram & TikTok

App web locale: incolli il link di un reel/post Instagram o di un video TikTok e scarichi l'MP4.

## Avvio

```bash
cd video-downloader
pip install -r requirements.txt
python app.py            # si apre http://localhost:8000
```

Consigliato installare **ffmpeg** (`brew install ffmpeg`, `winget install ffmpeg`, `apt install ffmpeg`) per avere sempre audio+video uniti alla qualità migliore.

## Dal telefono

**Con il computer acceso (stessa Wi-Fi):** avvia `python app.py --telefono`, poi apri sul telefono l'indirizzo che compare nel terminale (es. `http://192.168.1.20:8000`). Il video finisce nei Download (Android) o in File → Download (iPhone); da lì "Salva video" per metterlo in Galleria/Foto. Se non si apre, consenti Python nel firewall del computer.

**Senza computer, su Android:** installa [Termux](https://f-droid.org/packages/com.termux/) da F-Droid, poi:

```bash
pkg install python ffmpeg git
git clone -b ccr-e3bf69b6-oq3rp2 https://github.com/gabrieletramonte-sudo/Colori.git && cd Colori/video-downloader
pip install -r requirements.txt
python app.py --no-browser      # poi apri http://localhost:8000 nel browser del telefono
```

## Sul tuo VPS (usala da qualsiasi telefono)

Su un VPS Debian/Ubuntu, collegato in SSH:

```bash
curl -fsSL https://raw.githubusercontent.com/gabrieletramonte-sudo/Colori/ccr-e3bf69b6-oq3rp2/video-downloader/deploy/install.sh | sudo bash
```

Ti chiede la password del sito, poi stampa l'indirizzo da aprire. Con un dominio che punta al VPS hai l'HTTPS automatico (consigliato, così la password non viaggia in chiaro):

```bash
curl -fsSL https://raw.githubusercontent.com/gabrieletramonte-sudo/Colori/ccr-e3bf69b6-oq3rp2/video-downloader/deploy/install.sh | sudo DOMAIN=video.tuodominio.it bash
```

Rilanciare lo stesso comando aggiorna l'app. yt-dlp si aggiorna da solo ogni notte. Log: `journalctl -u scarica-video -f`.
Instagram blocca spesso gli IP dei server: carica un `cookies.txt` in `/var/lib/scarica-video/cookies.txt` (proprietario `scarica`) e `sudo systemctl restart scarica-video`.

## Instagram: accesso richiesto

Instagram spesso blocca i download senza login (sempre per i profili privati). In quel caso:

- **Cookie dal browser** dove sei loggato su Instagram:
  `COOKIES_FROM_BROWSER=chrome python app.py` (anche `firefox`, `safari`, `edge`, `brave`)
  Su Windows (PowerShell): `$env:COOKIES_FROM_BROWSER="chrome"; python app.py`
- **Oppure** esporta un file `cookies.txt` (formato Netscape, es. con l'estensione "Get cookies.txt LOCALLY") e mettilo in questa cartella. È già in `.gitignore`: non committarlo mai.

## Opzioni

| Variabile | Default | |
|---|---|---|
| `PORT` | `8000` | porta del server |
| `HOST` | `127.0.0.1` | metti `0.0.0.0` per usarla dal telefono sulla stessa rete Wi-Fi |
| `COOKIES_FROM_BROWSER` | — | browser da cui leggere i cookie |
| `COOKIES_FILE` | `./cookies.txt` | percorso del file cookie |
| `APP_PASSWORD` | — | se impostata il sito chiede la password |
| `MAX_PARALLEL` | `3` | download contemporanei massimi |

`python app.py --no-browser` avvia senza aprire il browser.

## Se smette di funzionare

Instagram e TikTok cambiano spesso: aggiorna il motore di download con
`pip install -U yt-dlp`.

> Scarica solo contenuti tuoi o che hai il diritto di usare, nel rispetto dei termini delle piattaforme e del diritto d'autore.
