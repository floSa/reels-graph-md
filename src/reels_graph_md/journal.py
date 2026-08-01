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
        self._index_natif = self._construire_index_natif()

    def _construire_index_natif(self) -> dict[str, str]:
        """Index inverse identifiant natif -> URL déjà traitée.

        Reconstruit en mémoire au chargement plutôt que persisté à côté des
        entrées : le fichier reste un dict plat `URL -> entrée`, lisible à l'œil
        et sans structure parallèle à maintenir cohérente.
        """
        index: dict[str, str] = {}
        for url, entree in self.entrees.items():
            natif = entree.get("natif")
            if natif and entree.get("statut") == "ok" and not entree.get("alias_de"):
                index.setdefault(natif, url)
        return index

    def est_fait(self, url: str) -> bool:
        return self.entrees.get(url, {}).get("statut") in ("ok", "impossible")

    def a_traiter(self, urls: list[str]) -> list[str]:
        """Les URLs qui restent à faire — les échecs sont automatiquement retentés.

        Trois états, et la distinction compte. `ok` est traité, `echec` est
        transitoire donc retenté, `impossible` est structurel : le retenter à
        chaque lancement ne produirait jamais rien d'autre que la même erreur.
        """
        return [u for u in urls if not self.est_fait(u)]

    def impossible(self, url: str, raison: str) -> None:
        """Marque une URL comme définitivement hors d'atteinte.

        Cas rencontré : un carrousel photo dont `yt-dlp --dump-json` ne tire
        rien, pas même la légende. La cause ne passera pas avec le temps ;
        compter ces posts en échec les ferait retenter éternellement et
        gonflerait le compteur d'échecs sans que rien ne soit réparable.
        """
        self.entrees[url] = {
            "statut": "impossible",
            "le": f"{datetime.now():%Y-%m-%d %H:%M}",
            "raison": str(raison).replace("\n", " ")[:200],
        }
        self.sauver()

    def url_pour_natif(self, natif: str) -> str | None:
        """L'URL déjà traitée qui porte cet identifiant natif, s'il y en a une.

        C'est ce qui rattrape les doublons que la canonicalisation d'URL ne peut
        pas voir : un lien court `vm.tiktok.com/ZGabc` et sa forme résolue
        `tiktok.com/@compte/video/7412…` sont deux chaînes irréconciliables tant
        qu'on n'a pas interrogé la plateforme. L'identifiant qu'elle renvoie,
        lui, est la vraie identité du reel.
        """
        return self._index_natif.get(natif)

    def succes(self, url: str, **details) -> None:
        self.entrees[url] = {
            "statut": "ok",
            "le": f"{datetime.now():%Y-%m-%d %H:%M}",
            **details,
        }
        natif = details.get("natif")
        if natif and not details.get("alias_de"):
            self._index_natif.setdefault(natif, url)
        self.sauver()

    def remettre_en_file(self, url: str, raison: str) -> None:
        """Redéclasse une entrée `ok` en échec pour qu'elle soit refaite.

        Sert à la réparation : une fiche ou une vidéo supprimée du disque laisse
        une entrée `ok` mensongère, qui fait sauter le reel indéfiniment. On
        retire aussi l'entrée de l'index natif, sans quoi le reel refait serait
        immédiatement classé comme doublon de lui-même.
        """
        natif = self.entrees.get(url, {}).get("natif")
        if natif and self._index_natif.get(natif) == url:
            del self._index_natif[natif]
        self.echec(url, raison)

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
        compte = {"ok": 0, "echec": 0, "impossible": 0}
        for entree in self.entrees.values():
            statut = entree.get("statut", "echec")
            compte[statut] = compte.get(statut, 0) + 1
        return compte
