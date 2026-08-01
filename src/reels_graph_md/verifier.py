"""Vérification et réparation du vault : confronte le journal au disque.

    uv run reels-verifier --vault ~/Vault
    uv run reels-verifier --vault ~/Vault --reparer
    uv run reels-verifier --vault ~/Vault --a-enrichir

Le journal seul ne suffit pas. Il enregistre ce qui a été fait, pas ce qui est
encore là. Une fiche effacée par erreur, une vidéo supprimée pour gagner de la
place, un `.temp` interrompu : l'entrée reste `ok`, le reel est sauté à chaque
relance, et le trou ne se voit jamais.

`--reparer` redéclasse les entrées mensongères en échec, ce qui les remet
automatiquement dans la file du prochain `reels-ingest`. Rien n'est supprimé :
la réparation ne fait qu'ouvrir la voie à un retraitement.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .journal import Journal
from .mailler import lire_frontmatter

# Ordre d'affichage : d'abord ce qui casse la reprise, ensuite ce qui encombre.
CATEGORIES = {
    "fiche_manquante": "entrées `ok` dont la fiche n'existe plus",
    "video_manquante": "entrées `ok` dont la vidéo n'existe plus",
    "alias_orphelin": "doublons pointant une entrée disparue",
    "fiche_orpheline": "fiches sur le disque absentes du journal",
    "video_orpheline": "vidéos sur le disque qu'aucune fiche n'utilise",
    "a_enrichir": "fiches sans thème ni entité (étape d'enrichissement)",
    "a_verifier": "fiches marquées pour une reprise manuelle (contenu non exploitable)",
}

REPARABLES = ("fiche_manquante", "video_manquante", "alias_orphelin")


def auditer(vault: Path) -> dict[str, list[str]]:
    """Confronte journal et disque. Renvoie les anomalies par catégorie.

    Fonction pure au sens où elle ne modifie rien : la réparation est une
    décision distincte, prise par l'appelant.
    """
    carnet = Journal(vault / "journal.json")
    dossier_fiches = vault / "fiches"
    dossier_reels = vault / "reels"

    resultats: dict[str, list[str]] = {cle: [] for cle in CATEGORIES}

    fiches_attendues: set[str] = set()
    videos_attendues: set[str] = set()

    for url, entree in carnet.entrees.items():
        if entree.get("statut") != "ok":
            continue

        origine = entree.get("alias_de")
        if origine:
            reference = carnet.entrees.get(origine, {})
            if reference.get("statut") != "ok":
                resultats["alias_orphelin"].append(url)
            continue

        nom_fiche = entree.get("fiche")
        if nom_fiche:
            fiches_attendues.add(nom_fiche)
            if not (dossier_fiches / nom_fiche).exists():
                resultats["fiche_manquante"].append(url)

        chemin_video = entree.get("video")
        if chemin_video:
            videos_attendues.add(Path(chemin_video).name)
            if not (vault / chemin_video).exists():
                resultats["video_manquante"].append(url)

    if dossier_fiches.is_dir():
        for chemin in sorted(dossier_fiches.glob("*.md")):
            if chemin.name not in fiches_attendues:
                resultats["fiche_orpheline"].append(chemin.name)
            entete = lire_frontmatter(chemin.read_text(encoding="utf-8", errors="ignore"))
            if not entete.get("themes") and not entete.get("entites"):
                resultats["a_enrichir"].append(chemin.name)
            if entete.get("statut") == "a_verifier":
                resultats["a_verifier"].append(chemin.name)

    if dossier_reels.is_dir():
        for chemin in sorted(dossier_reels.iterdir()):
            if chemin.is_file() and chemin.name not in videos_attendues:
                resultats["video_orpheline"].append(chemin.name)

    return resultats


def reparer(vault: Path, resultats: dict[str, list[str]]) -> int:
    """Redéclasse en échec les entrées que le disque contredit. Renvoie le compte."""
    carnet = Journal(vault / "journal.json")
    raisons = {
        "fiche_manquante": "fiche absente du disque",
        "video_manquante": "vidéo absente du disque",
        "alias_orphelin": "l'entrée d'origine a disparu",
    }
    compte = 0
    for categorie in REPARABLES:
        for url in resultats.get(categorie, []):
            carnet.remettre_en_file(url, raisons[categorie])
            compte += 1
    return compte


def main() -> int:
    parseur = argparse.ArgumentParser(
        prog="reels-verifier",
        description="Confronte le journal au contenu réel du vault.",
    )
    parseur.add_argument("--vault", default=str(Path.home() / "Vault"))
    parseur.add_argument(
        "--reparer",
        action="store_true",
        help="redéclasser en échec les entrées que le disque contredit, "
        "pour qu'elles repassent au prochain reels-ingest",
    )
    parseur.add_argument(
        "--a-enrichir",
        action="store_true",
        help="lister uniquement les chemins des fiches restant à enrichir, "
        "un par ligne (sortie exploitable par un autre outil)",
    )
    args = parseur.parse_args()

    vault = Path(args.vault).expanduser()
    if not (vault / "journal.json").exists():
        print(f"Aucun journal dans {vault} — rien à vérifier.", file=sys.stderr)
        return 2

    resultats = auditer(vault)

    if args.a_enrichir:
        for nom in resultats["a_enrichir"]:
            print(vault / "fiches" / nom)
        return 0

    anomalies = 0
    for cle, libelle in CATEGORIES.items():
        elements = resultats[cle]
        if not elements:
            continue
        if cle not in ("a_enrichir", "a_verifier"):
            anomalies += len(elements)
        print(f"\n{len(elements)} {libelle}")
        for element in elements[:10]:
            print(f"  {element}")
        if len(elements) > 10:
            print(f"  … et {len(elements) - 10} autres")

    if not anomalies and not resultats["a_enrichir"] and not resultats["a_verifier"]:
        print("Vault cohérent : le journal et le disque concordent.")
        return 0

    if args.reparer:
        compte = reparer(vault, resultats)
        print(f"\n{compte} entrée(s) remises en file. Relance `reels-ingest` pour les refaire.")
        return 0

    if anomalies:
        print("\nRelance avec --reparer pour remettre ces entrées en file.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
