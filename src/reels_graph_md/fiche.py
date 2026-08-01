"""Écriture de la fiche Markdown d'un reel.

Cette étape est purement mécanique : elle assemble ce que le pipeline a récolté,
sans jamais rédiger. La synthèse, les thèmes et les entités sont ajoutés ensuite
par le LLM (étape 8), qui remplit les sections laissées en attente.

Sur les horodatages : contrairement à YouTube, Instagram, TikTok et Facebook
n'honorent pas de paramètre `?t=` dans leurs URLs. Un lien horodaté vers le post
d'origine ne marcherait pas. Les repères `[MM:SS]` renvoient donc à la vidéo
locale, embarquée en tête de fiche — que le post d'origine survive ou non.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

MARQUEUR_SYNTHESE = "<!-- synthese:en-attente -->"

# Un transcript plus court que ça ne porte pas d'information exploitable : c'est
# un reel musical, une punchline, ou un échec de transcription.
SEUIL_MOTS_FIABLE = 25
SEUIL_MOTS_MINIMAL = 5


def _yaml(valeur) -> str:
    """Sérialise une valeur en YAML sûr.

    Les légendes de reels sont pleines de `:`, de `#`, d'emojis et de guillemets.
    Non échappées, elles cassent le frontmatter — et Obsidian n'affiche alors
    aucune propriété, en silence. On guillemette systématiquement les chaînes.
    """
    if valeur is None or valeur == "":
        return '""'
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    if isinstance(valeur, (int, float)):
        return str(valeur)
    if isinstance(valeur, (list, tuple)):
        return "[" + ", ".join(_yaml(v) for v in valeur) + "]"
    texte = str(valeur).replace("\\", "\\\\").replace('"', '\\"')
    texte = texte.replace("\n", " ").replace("\r", " ")
    return f'"{texte}"'


def _compter_mots(texte: str) -> int:
    return len(re.findall(r"\w+", texte or ""))


def evaluer_fiabilite(transcript: str, legende: str) -> str:
    """Dit à quel point la fiche est exploitable — et le dit honnêtement.

    C'est la réponse à la limite que reels-vault assume : « ce n'est pas de la
    magie, c'est de la transcription ». Sans voix off, la fiche est vide, et il
    vaut mieux l'étiqueter que laisser croire à un traitement réussi.
    """
    mots = _compter_mots(transcript)
    if mots >= SEUIL_MOTS_FIABLE:
        return "haute"
    if mots >= SEUIL_MOTS_MINIMAL:
        return "moyenne"
    if _compter_mots(legende) >= SEUIL_MOTS_MINIMAL:
        return "legende_seule"
    return "vide"


def _horodatage(secondes: float) -> str:
    total = int(secondes)
    return f"[{total // 60:02d}:{total % 60:02d}]"


def formater_segments(segments: list[dict]) -> str:
    return "\n".join(f"{_horodatage(s['start'])} {s['text']}" for s in segments)


def construire(
    *,
    identifiant: str,
    url: str,
    plateforme: str,
    meta: dict,
    transcript: str,
    transcript_captions: str = "",
    source_transcript: str = "",
    chemin_video: str | None = None,
) -> str:
    """Rend la fiche complète en Markdown."""
    legende = (meta.get("description") or "").strip()
    titre = (meta.get("title") or identifiant).strip().replace("\n", " ")[:120]
    auteur = meta.get("uploader") or meta.get("channel") or meta.get("uploader_id") or ""

    date_pub = meta.get("upload_date") or ""
    if re.fullmatch(r"\d{8}", str(date_pub)):
        date_pub = f"{date_pub[:4]}-{date_pub[4:6]}-{date_pub[6:]}"

    # yt-dlp rend une durée flottante ("62.367000579833984"), illisible dans un
    # frontmatter et sans intérêt à la milliseconde près.
    duree = meta.get("duration")
    duree = round(float(duree)) if isinstance(duree, (int, float)) else ""

    fiabilite = evaluer_fiabilite(transcript, legende)

    entete = "\n".join(
        [
            "---",
            f"source: {_yaml(url)}",
            f"plateforme: {_yaml(plateforme)}",
            f"auteur: {_yaml(auteur)}",
            f"compte_url: {_yaml(meta.get('uploader_url') or meta.get('channel_url') or '')}",
            f"date_publication: {_yaml(date_pub)}",
            f"duree_s: {_yaml(duree)}",
            f"langue: {_yaml(meta.get('language') or 'fr')}",
            f"vues: {_yaml(meta.get('view_count') or '')}",
            f"source_transcript: {_yaml(source_transcript)}",
            f"fiabilite: {_yaml(fiabilite)}",
            "themes: []",
            "entites: []",
            f"traite_le: {_yaml(f'{datetime.now():%Y-%m-%d}')}",
            "statut: brut",
            "---",
        ]
    )

    corps = [entete, "", f"# {titre}", ""]

    if chemin_video:
        corps += [f"![[{chemin_video}]]", ""]

    corps += [
        f"> [!info] [Voir le post d'origine]({url})"
        + (f" — {auteur}" if auteur else ""),
        "",
        MARQUEUR_SYNTHESE,
        "",
        "> [!abstract] En une phrase",
        "> *(à compléter)*",
        "",
        "## Ce que dit le reel",
        "",
        "*(à compléter)*",
        "",
        "## Affirmations vérifiables",
        "",
        "*(à compléter)*",
        "",
        "## Entités citées",
        "",
        "*(à compléter)*",
        "",
        "## Légende du post",
        "",
        legende or "*(aucune légende)*",
        "",
        "## Transcript",
        "",
    ]

    if transcript.strip():
        corps.append(transcript.strip())
    else:
        corps.append("*(pas d'audio exploitable)*")

    if transcript_captions.strip():
        corps += [
            "",
            "## Transcript — sous-titres de la plateforme",
            "",
            "> [!note] Deuxième source, à croiser avec la précédente.",
            "> Une divergence entre les deux signale un passage à vérifier,",
            "> typiquement un nom propre. Ne pas recopier l'une des deux sans regarder l'autre.",
            "",
            transcript_captions.strip(),
        ]

    return "\n".join(corps) + "\n"


def ecrire(dossier: Path, identifiant: str, contenu: str) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"{identifiant}.md"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin
