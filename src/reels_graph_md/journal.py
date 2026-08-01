"""Journal de traitement — c'est lui qui rend l'ingestion reprenable.

Écrit sur disque après *chaque* reel, pas en fin de run : un Ctrl+C, une coupure
réseau ou un rate-limit à la 180e vidéo ne coûtent que la vidéo en cours.

La clé est l'URL **canonique** (cf. liens.normaliser). reels-vault utilise l'URL
brute, si bien que deux variantes du même post créent deux entrées de journal
alors qu'elles produisent un seul fichier de fiche.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Journal:
    def __init__(self, chemin: Path):
        self.chemin = chemin
        self.entrees: dict[str, dict] = {}
        if chemin.exists():
            try:
                self.entrees = json.loads(chemin.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                # Un journal corrompu ne doit pas empêcher de repartir : on
                # repart de zéro, les fiches déjà écrites seront réécrites.
                self.entrees = {}

    def est_fait(self, url: str) -> bool:
        return self.entrees.get(url, {}).get("statut") == "ok"

    def a_traiter(self, urls: list[str]) -> list[str]:
        """Les URLs qui restent à faire — les échecs sont automatiquement retentés."""
        return [u for u in urls if not self.est_fait(u)]

    def succes(self, url: str, **details) -> None:
        self.entrees[url] = {
            "statut": "ok",
            "le": f"{datetime.now():%Y-%m-%d %H:%M}",
            **details,
        }
        self.sauver()

    def echec(self, url: str, erreur: str) -> None:
        precedent = self.entrees.get(url, {})
        self.entrees[url] = {
            "statut": "echec",
            "le": f"{datetime.now():%Y-%m-%d %H:%M}",
            "erreur": str(erreur).replace("\n", " ")[:300],
            "tentatives": precedent.get("tentatives", 0) + 1,
        }
        self.sauver()

    def sauver(self) -> None:
        # Écriture atomique : une coupure pendant l'écriture laisserait sinon un
        # journal tronqué, donc illisible, donc tout le stock à refaire.
        provisoire = self.chemin.with_suffix(".json.tmp")
        provisoire.write_text(
            json.dumps(self.entrees, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        provisoire.replace(self.chemin)

    def resume(self) -> dict[str, int]:
        compte = {"ok": 0, "echec": 0}
        for entree in self.entrees.values():
            statut = entree.get("statut", "echec")
            compte[statut] = compte.get(statut, 0) + 1
        return compte
