"""Tests de l'audit du vault : le journal dit ce qui a été fait, pas ce qui reste."""

from reels_graph_md import verifier
from reels_graph_md.journal import Journal

FRONTMATTER_ENRICHI = '---\nthemes: ["politique"]\nentites: ["Assemblée"]\n---\n\n# Titre\n'
FRONTMATTER_BRUT = "---\nthemes: []\nentites: []\n---\n\n# Titre\n"


def _vault(tmp_path):
    for sous in ("fiches", "reels"):
        (tmp_path / sous).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _reel_complet(vault, nom="insta_A", enrichi=True):
    """Une entrée saine : journal + fiche + vidéo présents."""
    (vault / "fiches" / f"{nom}.md").write_text(
        FRONTMATTER_ENRICHI if enrichi else FRONTMATTER_BRUT, encoding="utf-8"
    )
    (vault / "reels" / f"{nom}.mp4").write_bytes(b"x")
    Journal(vault / "journal.json").succes(
        f"https://instagram.com/reel/{nom}",
        fiche=f"{nom}.md",
        video=f"reels/{nom}.mp4",
        natif=f"instagram:{nom}",
    )


class TestVaultSain:
    def test_aucune_anomalie(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        resultats = verifier.auditer(vault)
        assert all(not v for v in resultats.values())


class TestAnomalies:
    def test_fiche_supprimee(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        (vault / "fiches" / "insta_A.md").unlink()
        assert verifier.auditer(vault)["fiche_manquante"] == [
            "https://instagram.com/reel/insta_A"
        ]

    def test_video_supprimee(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        (vault / "reels" / "insta_A.mp4").unlink()
        assert verifier.auditer(vault)["video_manquante"] == [
            "https://instagram.com/reel/insta_A"
        ]

    def test_fiche_orpheline(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        (vault / "fiches" / "venue_d_ailleurs.md").write_text(
            FRONTMATTER_ENRICHI, encoding="utf-8"
        )
        assert verifier.auditer(vault)["fiche_orpheline"] == ["venue_d_ailleurs.md"]

    def test_video_orpheline(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        (vault / "reels" / "restee_la.mp4").write_bytes(b"x")
        assert verifier.auditer(vault)["video_orpheline"] == ["restee_la.mp4"]

    def test_alias_orphelin(self, tmp_path):
        vault = _vault(tmp_path)
        carnet = Journal(vault / "journal.json")
        carnet.succes(
            "https://vm.tiktok.com/ZG",
            natif="tiktok:1",
            alias_de="https://tiktok.com/@u/video/1",
        )
        assert verifier.auditer(vault)["alias_orphelin"] == ["https://vm.tiktok.com/ZG"]

    def test_alias_valide_n_est_pas_signale(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        Journal(vault / "journal.json").succes(
            "https://instagram.com/p/autre",
            natif="instagram:insta_A",
            alias_de="https://instagram.com/reel/insta_A",
        )
        assert verifier.auditer(vault)["alias_orphelin"] == []

    def test_fiche_non_enrichie(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault, enrichi=False)
        assert verifier.auditer(vault)["a_enrichir"] == ["insta_A.md"]


class TestReparation:
    def test_remet_en_file_et_le_reel_repasse(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault)
        url = "https://instagram.com/reel/insta_A"
        (vault / "fiches" / "insta_A.md").unlink()

        assert verifier.reparer(vault, verifier.auditer(vault)) == 1

        carnet = Journal(vault / "journal.json")
        assert not carnet.est_fait(url)
        assert carnet.a_traiter([url]) == [url]

    def test_libere_l_identifiant_natif(self, tmp_path):
        # Sans cela, le reel refait serait aussitôt classé comme doublon de
        # lui-même et ne serait jamais retraité.
        vault = _vault(tmp_path)
        _reel_complet(vault)
        (vault / "reels" / "insta_A.mp4").unlink()
        verifier.reparer(vault, verifier.auditer(vault))
        assert Journal(vault / "journal.json").url_pour_natif("instagram:insta_A") is None

    def test_ne_touche_pas_aux_fiches_a_enrichir(self, tmp_path):
        vault = _vault(tmp_path)
        _reel_complet(vault, enrichi=False)
        assert verifier.reparer(vault, verifier.auditer(vault)) == 0
        assert Journal(vault / "journal.json").est_fait("https://instagram.com/reel/insta_A")
