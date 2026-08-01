"""Appels à yt-dlp : métadonnées puis téléchargement.

Deux différences avec reels-vault, toutes deux issues de bugs constatés chez lui :

1. **Une seule passe de téléchargement.** reels-vault appelle yt-dlp deux fois
   par reel (l'audio, puis la vidéo), ce qui double l'exposition au rate-limit
   d'Instagram — le facteur limitant réel sur un gros stock. Ici on télécharge la
   vidéo une fois, et ffmpeg en extrait l'audio en local.

2. **Les échecs sont détectés.** reels-vault ne teste aucun code de retour : une
   erreur yt-dlp produit silencieusement une fiche vide, marquée `ok` dans le
   journal, donc jamais retentée. On vérifie que le fichier existe vraiment.

La nuance qui rend le point 2 délicat : yt-dlp sort en non-zéro quand une piste
de sous-titres échoue (un 429 sur la piste auto, très fréquent) alors que la
vidéo est parfaitement téléchargée. Le code de retour seul est donc trompeur
dans les deux sens. Le seul juge fiable est la présence du fichier.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

def _commande_ytdlp() -> list[str]:
    """Le binaire yt-dlp s'il est sur le PATH, sinon le module Python.

    Les deux formes existent dans la nature : `uv tool install yt-dlp` pose un
    binaire hors de l'environnement du projet, tandis qu'un `pip install yt-dlp`
    ne fournit que le module. reels-vault ne connaît que la seconde forme et
    échoue sur la première.
    """
    binaire = shutil.which("yt-dlp")
    return [binaire] if binaire else [sys.executable, "-m", "yt_dlp"]


YTDLP = _commande_ytdlp()

DELAI_METADONNEES = 120
DELAI_TELECHARGEMENT = 300

EXTENSIONS_VIDEO = (".mp4", ".mkv", ".webm", ".mov")

# Les reels sont courts : plafonner à 1080p suffit largement et garde les
# fichiers petits, tout en restant lisible si on veut revoir la vidéo.
FORMAT = "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b"

# fr d'abord : c'est la langue du corpus visé. `watch` code `en.*` en dur, ce qui
# fait que les sous-titres français ne sont jamais récupérés.
LANGUES_SOUS_TITRES = "fr.*,en.*"


class ErreurYtdlp(RuntimeError):
    """Échec attribuable à yt-dlp ou à la plateforme (post supprimé, privé, 429)."""


def verifier_outils() -> None:
    """Sort en erreur si yt-dlp ou ffmpeg manquent, avant de commencer le lot."""
    manquants = []

    try:
        subprocess.run(YTDLP + ["--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        manquants.append("yt-dlp   ->  uv tool install yt-dlp  (ou: uv pip install yt-dlp)")

    for binaire in ("ffmpeg", "ffprobe"):
        if shutil.which(binaire) is None:
            manquants.append(f"{binaire:8s} ->  apt install ffmpeg  /  winget install Gyan.FFmpeg")

    if manquants:
        raise SystemExit(
            "Outil(s) manquant(s) :\n  " + "\n  ".join(manquants)
        )


def options_cookies(cookies: str | None) -> list[str]:
    """`--cookies` accepte un nom de navigateur ou un chemin de cookies.txt.

    Rappel de terrain : sous Windows, Chrome 127+ chiffre ses cookies d'une façon
    que yt-dlp ne sait pas déchiffrer. Il faut Firefox, et le navigateur doit être
    complètement fermé — il verrouille son fichier de cookies.
    """
    if not cookies:
        return []
    chemin = Path(cookies).expanduser()
    if chemin.exists():
        return ["--cookies", str(chemin.resolve())]
    return ["--cookies-from-browser", cookies]


def metadonnees(url: str, cookies: str | None = None) -> dict:
    """Métadonnées du post sans rien télécharger.

    C'est ici qu'on récupère la **légende**, qui porte souvent plus d'information
    vérifiable que la voix off : liens, noms complets, sources citées.
    """
    commande = (
        YTDLP
        + ["--dump-json", "--no-warnings", "--skip-download", "--no-playlist"]
        + options_cookies(cookies)
        + ["--", url]
    )
    resultat = subprocess.run(
        commande, capture_output=True, text=True, timeout=DELAI_METADONNEES
    )
    if resultat.returncode != 0 or not resultat.stdout.strip():
        raise ErreurYtdlp((resultat.stderr or "yt-dlp a échoué sans message").strip()[:300])

    try:
        return json.loads(resultat.stdout.splitlines()[0])
    except (json.JSONDecodeError, IndexError) as exc:
        raise ErreurYtdlp(f"métadonnées illisibles : {exc}") from exc


IGNOREES = {".vtt", ".srt", ".json", ".part", ".ytdl", ".temp", ".description"}


def _trouver_media(dossier: Path, tige: str) -> Path | None:
    """Le fichier média produit par yt-dlp, quelle que soit son extension.

    On préfère un conteneur vidéo, mais on accepte tout le reste : le remux ne
    donne pas toujours du mp4, et un post exceptionnellement audio-only reste
    exploitable puisque seul le son sert à la transcription. Ne rien accepter
    d'autre ferait échouer un reel parfaitement téléchargé.
    """
    for extension in EXTENSIONS_VIDEO:
        for candidat in sorted(dossier.glob(f"{tige}*{extension}")):
            return candidat
    for candidat in sorted(dossier.glob(f"{tige}*")):
        if candidat.is_file() and candidat.suffix.lower() not in IGNOREES:
            return candidat
    return None


def _trouver_sous_titres(dossier: Path, tige: str) -> Path | None:
    candidats = sorted(dossier.glob(f"{tige}*.vtt"))
    if not candidats:
        return None
    # Les sous-titres manuels priment sur les automatiques, et le français sur
    # l'anglais : yt-dlp suffixe la langue dans le nom (video.fr.vtt).
    francais = [c for c in candidats if ".fr" in c.name]
    return francais[0] if francais else candidats[0]


def telecharger(
    url: str,
    dossier: Path,
    tige: str,
    cookies: str | None = None,
) -> tuple[Path, Path | None]:
    """Télécharge la vidéo et ses sous-titres. Renvoie (vidéo, sous-titres|None).

    Lève ErreurYtdlp si aucun fichier vidéo n'a été produit — c'est le seul
    critère fiable, le code de retour étant pollué par les échecs de sous-titres.
    """
    dossier.mkdir(parents=True, exist_ok=True)
    modele_sortie = str(dossier / f"{tige}.%(ext)s")

    commande = (
        YTDLP
        + [
            "-f", FORMAT,
            "--merge-output-format", "mp4",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", LANGUES_SOUS_TITRES,
            "--sub-format", "vtt",
            "--convert-subs", "vtt",
            "--no-playlist",
            "--no-warnings",
            "--quiet",
            "-o", modele_sortie,
        ]
        + options_cookies(cookies)
        + ["--", url]
    )

    resultat = subprocess.run(
        commande, capture_output=True, text=True, timeout=DELAI_TELECHARGEMENT
    )

    media = _trouver_media(dossier, tige)
    if media is None:
        message = (resultat.stderr or resultat.stdout or "").strip()
        # Lister ce qui a été produit change tout au diagnostic : un dossier vide
        # est un échec de téléchargement, un dossier avec un .part est une
        # coupure, un dossier avec seulement des .vtt est un post inaccessible.
        produits = sorted(p.name for p in dossier.glob(f"{tige}*")) or ["rien"]
        raise ErreurYtdlp(
            f"aucun média produit (code {resultat.returncode}, fichiers : "
            f"{', '.join(produits)}) : {message[:250] or 'aucun message'}"
        )

    return media, _trouver_sous_titres(dossier, tige)
