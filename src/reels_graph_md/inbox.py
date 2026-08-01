"""Flux continu : la boîte de réception `inbox.txt` du vault.

Le bootstrap se fait par les exports officiels, une fois. Ensuite, les reels
sauvegardés au fil de l'eau arrivent par un raccourci de partage mobile qui
ajoute simplement l'URL à la fin d'un fichier texte. Aucun format imposé : une
URL par ligne suffit, et le reste du pipeline s'en accommode puisqu'il lit tout
en texte brut.

Une fois traitées, les lignes sont déplacées vers `inbox-traite.txt` plutôt que
supprimées : l'inbox reste courte, mais rien n'est perdu.

Le point délicat est la concurrence. Le raccourci peut écrire pendant que
l'ingestion tourne. On ne réécrit donc jamais l'inbox à partir de ce qu'on avait
lu au départ — on la relit au moment de l'archivage et on n'en retire que les
lignes effectivement traitées. Une URL ajoutée entre-temps survit.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import liens

NOM_INBOX = "inbox.txt"
NOM_ARCHIVE = "inbox-traite.txt"


def chemin_inbox(vault: Path) -> Path:
    return vault / NOM_INBOX


def urls_de_la_ligne(ligne: str) -> list[str]:
    """Les URLs de contenu d'une ligne, sous forme canonique."""
    trouvees = []
    for brut in liens.MOTIF_LIEN.findall(ligne):
        brut = brut.rstrip(liens.FIN_PARASITE)
        if liens.est_contenu(brut):
            trouvees.append(liens.normaliser(brut))
    return trouvees


def consommer(vault: Path, urls_traitees: set[str]) -> int:
    """Archive les lignes de l'inbox dont toutes les URLs sont traitées.

    Renvoie le nombre de lignes archivées. Les lignes qui portent une URL encore
    en échec restent en place et repasseront au prochain lancement.
    """
    inbox = chemin_inbox(vault)
    if not inbox.exists():
        return 0

    try:
        lignes = inbox.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return 0

    gardees: list[str] = []
    archivees: list[str] = []

    for ligne in lignes:
        if not ligne.strip():
            continue  # les lignes vides ne survivent pas à un passage
        trouvees = urls_de_la_ligne(ligne)
        if trouvees and all(url in urls_traitees for url in trouvees):
            archivees.append(ligne)
        else:
            gardees.append(ligne)

    if not archivees:
        return 0

    archive = vault / NOM_ARCHIVE
    with archive.open("a", encoding="utf-8") as sortie:
        sortie.write(f"# archivé le {datetime.now():%Y-%m-%d %H:%M}\n")
        for ligne in archivees:
            sortie.write(ligne + "\n")

    # Écriture atomique : une coupure ici perdrait des URLs jamais traitées.
    provisoire = inbox.with_suffix(".txt.tmp")
    provisoire.write_text(
        "\n".join(gardees) + ("\n" if gardees else ""), encoding="utf-8"
    )
    provisoire.replace(inbox)

    return len(archivees)
