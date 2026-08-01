"""Pont vers le moteur de transcription du skill `watch`.

On ne recopie pas ces scripts : ils sont maintenus dans claude-skills et on veut
profiter de leurs corrections. On les importe depuis leur emplacement réel.

Ce qu'on en tire :
  - `whisper.transcribe_video()` : extraction audio ffmpeg + envoi au serveur
    Whisper local + segments horodatés, avec réessais et découpage.
  - `transcribe.parse_vtt()` : lecture des sous-titres de plateforme, avec
    l'effondrement des doublons roulants.

Le chemin est surchargeable par REELS_GRAPH_MD_WATCH_SCRIPTS pour ceux qui ont
claude-skills ailleurs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CHEMIN_DEFAUT = Path.home() / "mes_projets" / "claude-skills" / "watch" / "scripts"

_charge = False


def chemin_scripts() -> Path:
    surcharge = os.environ.get("REELS_GRAPH_MD_WATCH_SCRIPTS")
    return Path(surcharge).expanduser() if surcharge else CHEMIN_DEFAUT


def _charger() -> None:
    global _charge
    if _charge:
        return

    dossier = chemin_scripts()
    if not (dossier / "whisper.py").exists():
        raise SystemExit(
            f"Moteur de transcription introuvable dans {dossier}.\n"
            "Il vient du skill `watch` (claude-skills). Indique son emplacement "
            "avec REELS_GRAPH_MD_WATCH_SCRIPTS=/chemin/vers/watch/scripts"
        )

    # En tête de sys.path : whisper.py fait `from config import read_env_file`,
    # qui n'est résoluble que si son propre dossier est prioritaire.
    sys.path.insert(0, str(dossier))
    _charge = True


def whisper():
    _charger()
    import whisper as module  # noqa: PLC0415 — import différé volontaire

    return module


def transcribe():
    _charger()
    import transcribe as module  # noqa: PLC0415

    return module


def serveur_disponible() -> bool:
    """True si le serveur Whisper local répond. Un conteneur arrêté est un état normal."""
    return whisper().local_available()


def url_serveur() -> str:
    return whisper().local_base_url()


def transcrire(video: Path, audio_temp: Path, langue: str = "fr") -> list[dict]:
    """Transcrit une vidéo locale et renvoie des segments {start, end, text}.

    La langue est **forcée**, pas détectée. Sur un clip de 20 secondes avec de la
    musique, l'autodétection de Whisper se trompe régulièrement, et un transcript
    français décodé comme de l'anglais est inexploitable.
    """
    module = whisper()
    if langue:
        os.environ["WHISPER_LANGUAGE"] = langue
    segments, _ = module.transcribe_video(str(video), audio_temp)
    return segments


def lire_sous_titres(vtt: Path) -> list[dict]:
    """Segments issus d'un fichier VTT de plateforme, doublons roulants effondrés."""
    return transcribe().parse_vtt(str(vtt))


def formater(segments: list[dict]) -> str:
    """Transcript horodaté `[MM:SS] texte`."""
    return transcribe().format_transcript(segments)
