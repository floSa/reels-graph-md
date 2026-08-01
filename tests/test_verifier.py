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


class TestCoupeCircuit:
    """Un échec isolé est banal ; une série ne l'est pas."""

    def test_seuil_documente(self):
        from reels_graph_md.ingest import ECHECS_CONSECUTIFS_MAX
        assert ECHECS_CONSECUTIFS_MAX >= 3


class TestTranscriptionMuette:
    """Le moteur de watch signale tout par SystemExit, y compris l'absence de
    segments — ce qui tuait le lot entier, SystemExit n'étant pas une Exception."""

    def _moteur(self, monkeypatch, exc):
        from reels_graph_md import moteur

        class FauxWhisper:
            @staticmethod
            def transcribe_video(video, audio):
                raise exc

        monkeypatch.setattr(moteur, "whisper", lambda: FauxWhisper)
        return moteur

    def test_absence_de_segments_donne_une_liste_vide(self, monkeypatch, tmp_path):
        moteur = self._moteur(monkeypatch, SystemExit("Whisper returned no transcript segments"))
        assert moteur.transcrire(tmp_path / "v.mp4", tmp_path / "a.mp3") == []

    def test_piste_audio_absente_donne_une_liste_vide(self, monkeypatch, tmp_path):
        moteur = self._moteur(monkeypatch, SystemExit("ffmpeg produced no audio — video may have no audio track"))
        assert moteur.transcrire(tmp_path / "v.mp4", tmp_path / "a.mp3") == []

    def test_vraie_panne_devient_une_exception_ordinaire(self, monkeypatch, tmp_path):
        import pytest
        moteur = self._moteur(monkeypatch, SystemExit("Local Whisper server unreachable"))
        # RuntimeError, pas SystemExit : le lot doit survivre et ne perdre que ce reel.
        with pytest.raises(RuntimeError, match="transcription impossible"):
            moteur.transcrire(tmp_path / "v.mp4", tmp_path / "a.mp3")


class TestPostSansFormatVideo:
    """Certains posts annoncent une durée sans exposer de format téléchargeable.
    Les compter en échec les ferait retenter éternellement et sans espoir."""

    def _lancer(self, monkeypatch, tmp_path, erreur):
        from reels_graph_md import ingest, ytdlp

        monkeypatch.setattr(
            ytdlp, "metadonnees",
            lambda url, cookies: {"id": "X", "duration": 30, "description": "une légende bien assez longue pour compter"},
        )
        def faux_telecharger(*a, **k):
            raise ytdlp.ErreurYtdlp(erreur)
        monkeypatch.setattr(ytdlp, "telecharger", faux_telecharger)

        dossiers = {n: tmp_path / n for n in ("fiches", "reels", "temp")}
        for d in dossiers.values():
            d.mkdir(parents=True, exist_ok=True)
        from reels_graph_md.journal import Journal
        return ingest._traiter(
            "https://instagram.com/reel/X", dossiers, Journal(tmp_path / "j.json"), None, "fr"
        )

    def test_aucun_format_donne_une_fiche_legende(self, monkeypatch, tmp_path):
        details = self._lancer(monkeypatch, tmp_path, "No video formats found!")
        assert details["genre"] == "aucun format vidéo"
        assert details["fiabilite"] == "legende_seule"
        assert (tmp_path / "fiches" / "insta_X.md").exists()

    def test_une_vraie_panne_reste_un_echec(self, monkeypatch, tmp_path):
        import pytest
        from reels_graph_md import ytdlp
        with pytest.raises(ytdlp.ErreurYtdlp):
            self._lancer(monkeypatch, tmp_path, "HTTP Error 429: Too Many Requests")


class TestFiltreHallucinations:
    """Whisper comble une piste sans parole par des formules de générique.
    Le danger n'est pas le bruit mais la vraisemblance."""

    def _filtrer(self, textes):
        from reels_graph_md.moteur import filtrer_hallucinations
        segs = [{"start": i, "end": i + 1, "text": t} for i, t in enumerate(textes)]
        gardes, retires = filtrer_hallucinations(segs)
        return [s["text"] for s in gardes], retires

    def test_retire_les_formes_rencontrees_en_reel(self):
        gardes, retires = self._filtrer([
            "Sous-titres par Jérémy Diaz",
            "Sous-titrage ST' 501",
            "Sous-titrage Société Radio-Canada",
        ])
        assert gardes == [] and retires == 3

    def test_retire_les_formes_anglaises_et_les_sites(self):
        gardes, _ = self._filtrer([
            "Subtitles by the Amara.org community",
            "Thanks for watching!",
            "SousTitreur.com",
        ])
        assert gardes == []

    def test_conserve_un_vrai_transcript(self):
        vrais = [
            "Les députés ont adopté le texte hier soir.",
            "Trois cent douze voix pour.",
        ]
        gardes, retires = self._filtrer(vrais)
        assert gardes == vrais and retires == 0

    def test_ne_coupe_pas_une_phrase_qui_parle_de_sous_titres(self):
        # Un reel qui traite réellement du sous-titrage doit survivre : le motif
        # est ancré en début de segment, pas cherché n'importe où.
        phrase = "On va parler des sous-titres automatiques et de leurs limites."
        gardes, _ = self._filtrer([phrase])
        assert gardes == [phrase]

    def test_melange_reel_et_hallucination(self):
        gardes, retires = self._filtrer([
            "Bonjour à tous, aujourd'hui on parle du budget.",
            "Sous-titrage ST' 501",
        ])
        assert len(gardes) == 1 and retires == 1
