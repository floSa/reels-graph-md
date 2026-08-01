"""Tests des fonctions pures d'écriture de fiche et de maillage."""

from reels_md import fiche, mailler


class TestYamlSur:
    def test_echappe_les_guillemets_et_deux_points(self):
        # Une légende de reel réelle : `:` et `"` cassent un frontmatter non quoté
        # et Obsidian n'affiche alors aucune propriété, en silence.
        assert fiche._yaml('Titre : "le vrai" chiffre') == '"Titre : \\"le vrai\\" chiffre"'

    def test_aplatit_les_retours_ligne(self):
        assert "\n" not in fiche._yaml("ligne1\nligne2")

    def test_liste(self):
        assert fiche._yaml(["a", "b"]) == '["a", "b"]'

    def test_vide(self):
        assert fiche._yaml("") == '""'
        assert fiche._yaml(None) == '""'


class TestFiabilite:
    def test_haute_avec_un_vrai_transcript(self):
        assert fiche.evaluer_fiabilite(" ".join(["mot"] * 30), "") == "haute"

    def test_moyenne_sur_un_transcript_court(self):
        assert fiche.evaluer_fiabilite("un deux trois quatre cinq six", "") == "moyenne"

    def test_legende_seule_sans_audio(self):
        assert fiche.evaluer_fiabilite("", "une légende assez longue pour compter") == "legende_seule"

    def test_vide_quand_il_n_y_a_rien(self):
        assert fiche.evaluer_fiabilite("", "") == "vide"


class TestConstruction:
    def _fiche(self, **kw):
        defauts = dict(
            identifiant="insta_ABC",
            url="https://instagram.com/reel/ABC",
            plateforme="instagram",
            meta={"title": "Un titre", "uploader": "compte", "duration": 42,
                  "description": "légende : avec un deux-points",
                  "upload_date": "20260314"},
            transcript="[00:00] bonjour",
        )
        defauts.update(kw)
        return fiche.construire(**defauts)

    def test_frontmatter_parsable(self):
        entete = mailler.lire_frontmatter(self._fiche())
        assert entete["plateforme"] == "instagram"
        assert entete["auteur"] == "compte"
        assert entete["themes"] == []

    def test_convertit_la_date_yyyymmdd(self):
        assert mailler.lire_frontmatter(self._fiche())["date_publication"] == "2026-03-14"

    def test_embarque_la_video(self):
        rendu = self._fiche(chemin_video="reels/insta_ABC.mp4")
        assert "![[reels/insta_ABC.mp4]]" in rendu

    def test_legende_verbatim(self):
        assert "légende : avec un deux-points" in self._fiche()

    def test_signale_l_absence_d_audio(self):
        assert "(pas d'audio exploitable)" in self._fiche(transcript="")

    def test_section_captions_seulement_si_presente(self):
        assert "sous-titres de la plateforme" not in self._fiche()
        assert "sous-titres de la plateforme" in self._fiche(transcript_captions="[00:01] x")


class TestFrontmatter:
    def test_liste_avec_virgule_dans_un_element(self):
        texte = '---\nentites: ["Loi de finances, 2026", "Assemblée"]\n---\n'
        assert mailler.lire_frontmatter(texte)["entites"] == ["Loi de finances, 2026", "Assemblée"]

    def test_sans_frontmatter(self):
        assert mailler.lire_frontmatter("# Titre seul\n") == {}


class TestNomDeNote:
    def test_neutralise_les_caracteres_interdits(self):
        assert "/" not in mailler.nom_de_note("Budget 2026 / PLF")
        assert ":" not in mailler.nom_de_note("Loi : finances")


class TestMaillage:
    def _vault(self, tmp_path, themes, entites):
        dossier = tmp_path / "fiches"
        dossier.mkdir()
        (dossier / "insta_A.md").write_text(
            f"---\nthemes: {themes}\nentites: {entites}\n---\n\n# Le titre A\n",
            encoding="utf-8",
        )
        return tmp_path, dossier

    def test_pose_les_liens(self, tmp_path):
        vault, dossier = self._vault(tmp_path, '["politique"]', '["Assemblée nationale"]')
        f = mailler.collecter(dossier)[0]
        assert mailler.poser_liens(f) is True
        texte = f["chemin"].read_text(encoding="utf-8")
        assert "[[politique]]" in texte
        assert "[[Assemblée nationale]]" in texte

    def test_idempotent(self, tmp_path):
        vault, dossier = self._vault(tmp_path, '["politique"]', "[]")
        f = mailler.collecter(dossier)[0]
        assert mailler.poser_liens(f) is True
        # Deuxième passe : rien à changer, et surtout pas de section empilée
        assert mailler.poser_liens(f) is False
        assert f["chemin"].read_text(encoding="utf-8").count(mailler.MARQUEUR) == 1

    def test_ignore_une_fiche_non_enrichie(self, tmp_path):
        vault, dossier = self._vault(tmp_path, "[]", "[]")
        assert mailler.poser_liens(mailler.collecter(dossier)[0]) is False

    def test_note_index_liste_les_reels(self, tmp_path):
        vault, dossier = self._vault(tmp_path, '["politique"]', "[]")
        fiches = mailler.collecter(dossier)
        chemin = mailler.ecrire_note_index(vault / "themes", "politique", fiches, "theme")
        assert "[[insta_A|Le titre A]]" in chemin.read_text(encoding="utf-8")
