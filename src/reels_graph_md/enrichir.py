"""Application mécanique d'un lot d'enrichissement (étape 8).

    uv run reels-enrichir --vault ~/Vault --depuis lot.json

Le LLM lit les fiches et produit un JSON ; ce script l'applique. La séparation
est délibérée et reprend le principe du reste du projet : le code fait le
mécanique, le LLM fait l'éditorial.

Elle apporte trois choses que l'édition fiche par fiche n'a pas :

- **la reproductibilité** — le rendu Markdown est écrit une fois, pas réinventé
  à chaque fiche ;
- **la validation** — un thème vide, une entité en double, une fiche inconnue
  sont signalés au lieu de passer dans le vault ;
- **l'idempotence** — réappliquer un lot corrige les fiches au lieu d'empiler
  des sections.

Format attendu, un objet par identifiant de fiche :

    {
      "insta_ABC": {
        "phrase": "Le reel affirme que …",
        "themes": ["politique", "budget de l'État"],
        "entites": [{"type": "Institution", "nom": "Assemblée nationale"}],
        "ce_que_dit": "Texte libre, avec des repères [00:14].",
        "affirmations": ["[00:22] — « 312 voix pour »"]
      }
    }

`affirmations` peut être vide : toutes les fiches ne portent pas de fait
vérifiable, et en inventer serait pire que de laisser la section vide.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .fiche import MARQUEUR_SYNTHESE, _yaml

RIEN = "*(rien d'exploitable)*"


class ErreurLot(ValueError):
    """Le lot est mal formé — on refuse de l'appliquer plutôt que d'abîmer le vault."""


def _remplacer_section(texte: str, titre: str, contenu: str) -> str:
    """Remplace le corps d'une section `## <titre>` jusqu'au prochain titre."""
    motif = re.compile(
        rf"^## {re.escape(titre)}\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
    )
    if not motif.search(texte):
        raise ErreurLot(f"section « {titre} » introuvable")
    return motif.sub(f"## {titre}\n\n{contenu.strip()}\n\n", texte, count=1)


def _remplacer_liste(texte: str, cle: str, valeurs: list[str]) -> str:
    motif = re.compile(rf"^{cle}: \[.*?\]$", re.MULTILINE)
    if not motif.search(texte):
        raise ErreurLot(f"champ « {cle} » introuvable dans le frontmatter")
    return motif.sub(f"{cle}: {_yaml(valeurs)}", texte, count=1)


def valider(identifiant: str, donnees: dict) -> None:
    """Refuse ce qui produirait un maillage incohérent."""
    if not str(donnees.get("phrase", "")).strip():
        raise ErreurLot("`phrase` est vide")

    themes = donnees.get("themes") or []
    if not themes:
        raise ErreurLot("aucun thème — la fiche resterait invisible au maillage")
    for t in themes:
        if not str(t).strip():
            raise ErreurLot("thème vide")
        if str(t) != str(t).strip():
            raise ErreurLot(f"thème « {t} » avec des espaces en bordure")

    noms = [str(e.get("nom", "")).strip() for e in donnees.get("entites") or []]
    if any(not n for n in noms):
        raise ErreurLot("entité sans nom")
    if len(noms) != len(set(noms)):
        raise ErreurLot("entité en double dans la même fiche")


def appliquer(chemin: Path, donnees: dict) -> None:
    """Réécrit une fiche avec sa synthèse. Idempotent."""
    texte = chemin.read_text(encoding="utf-8")

    themes = [str(t).strip() for t in donnees.get("themes") or []]
    entites = donnees.get("entites") or []
    noms = [str(e["nom"]).strip() for e in entites]

    # Instagram ne fournit aucun titre : yt-dlp rend « Video by <compte> », qui
    # se retrouve tel quel dans chaque note de thème et d'entité. Un vault où
    # toutes les entrées s'appellent « Video by … » est illisible, et c'est
    # précisément ce qui doit servir à naviguer.
    titre = str(donnees.get("titre") or "").strip()
    if titre:
        texte = re.sub(r"^# .*$", f"# {titre}", texte, count=1, flags=re.MULTILINE)

    texte = _remplacer_liste(texte, "themes", themes)
    texte = _remplacer_liste(texte, "entites", noms)
    texte = re.sub(r"^statut: brut$", "statut: enrichi", texte, count=1, flags=re.MULTILINE)

    phrase = str(donnees["phrase"]).strip()
    texte = re.sub(
        r"> \[!abstract\] En une phrase\n> .*",
        f"> [!abstract] En une phrase\n> {phrase}",
        texte,
        count=1,
    )

    texte = _remplacer_section(
        texte, "Ce que dit le reel", str(donnees.get("ce_que_dit") or RIEN)
    )

    affirmations = [str(a).strip() for a in donnees.get("affirmations") or [] if str(a).strip()]
    texte = _remplacer_section(
        texte,
        "Affirmations vérifiables",
        "\n".join(f"- {a}" for a in affirmations) if affirmations else RIEN,
    )

    if entites:
        lignes = ["| Type | Nom |", "|---|---|"]
        lignes += [f"| {e.get('type', '—')} | {e['nom']} |" for e in entites]
        tableau = "\n".join(lignes)
    else:
        tableau = RIEN
    texte = _remplacer_section(texte, "Entités citées", tableau)

    texte = texte.replace(MARQUEUR_SYNTHESE + "\n\n", "").replace(MARQUEUR_SYNTHESE + "\n", "")
    chemin.write_text(texte, encoding="utf-8")


def main() -> int:
    parseur = argparse.ArgumentParser(
        prog="reels-enrichir",
        description="Applique un lot d'enrichissement produit par le LLM.",
    )
    parseur.add_argument("--vault", default=str(Path.home() / "Vault"))
    parseur.add_argument("--depuis", required=True, help="fichier JSON du lot, ou - pour stdin")
    parseur.add_argument(
        "--verifier-seulement",
        action="store_true",
        help="valider le lot sans rien écrire",
    )
    args = parseur.parse_args()

    brut = sys.stdin.read() if args.depuis == "-" else Path(args.depuis).read_text(encoding="utf-8")
    try:
        lot = json.loads(brut)
    except json.JSONDecodeError as exc:
        print(f"JSON illisible : {exc}", file=sys.stderr)
        return 2

    dossier = Path(args.vault).expanduser() / "fiches"
    problemes: list[str] = []
    a_ecrire: list[tuple[Path, dict]] = []

    for identifiant, donnees in lot.items():
        chemin = dossier / f"{identifiant}.md"
        if not chemin.exists():
            problemes.append(f"{identifiant} : fiche introuvable")
            continue
        try:
            valider(identifiant, donnees)
        except ErreurLot as exc:
            problemes.append(f"{identifiant} : {exc}")
            continue
        a_ecrire.append((chemin, donnees))

    if problemes:
        print(f"{len(problemes)} problème(s) — rien n'a été écrit :", file=sys.stderr)
        for p in problemes:
            print(f"  {p}", file=sys.stderr)
        return 1

    if args.verifier_seulement:
        print(f"{len(a_ecrire)} fiche(s) valides.")
        return 0

    for chemin, donnees in a_ecrire:
        appliquer(chemin, donnees)

    themes = sorted({t for d in lot.values() for t in d.get("themes") or []})
    entites = sorted({e["nom"] for d in lot.values() for e in d.get("entites") or []})
    print(f"{len(a_ecrire)} fiche(s) enrichie(s).")
    print(f"{len(themes)} thèmes : {', '.join(themes)}")
    print(f"{len(entites)} entités.")
    print("Lance `reels-mailler` pour régénérer le maillage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
