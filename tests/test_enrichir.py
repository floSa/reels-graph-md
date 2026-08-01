"""Tests de l'application d'un lot d'enrichissement."""

import pytest

from reels_graph_md import enrichir, fiche, mailler


def _fiche_brute(tmp_path, nom="insta_A"):
    dossier = tmp_path / "fiches"
    contenu = fiche.construire(
        identifiant=nom, url=f"https://instagram.com/reel/{nom}",
        plateforme="instagram", meta={"title": "Un titre", "duration": 40},
        transcript="[00:00] bonjour tout le monde",
    )
    return fiche.ecrire(dossier, nom, contenu)


LOT = {
    "phrase": "Le reel affirme que le texte a été adopté.",
    "themes": ["politique"],
    "entites": [{"type": "Institution", "nom": "Assemblée nationale"}],
    "ce_que_dit": "Reformulation fidèle, [00:14] sur le passage clé.",
    "affirmations": ["[00:22] — « 312 voix pour »"],
}


class TestApplication:
    def test_remplit_le_frontmatter(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, LOT)
        entete = mailler.lire_frontmatter(c.read_text(encoding="utf-8"))
        assert entete["themes"] == ["politique"]
        assert entete["entites"] == ["Assemblée nationale"]
        assert entete["statut"] == "enrichi"

    def test_remplit_le_corps(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, LOT)
        t = c.read_text(encoding="utf-8")
        assert "Le reel affirme que le texte a été adopté." in t
        assert "- [00:22] — « 312 voix pour »" in t
        assert "| Institution | Assemblée nationale |" in t
        assert "*(à compléter)*" not in t
        assert fiche.MARQUEUR_SYNTHESE not in t

    def test_preserve_le_transcript(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, LOT)
        assert "[00:00] bonjour tout le monde" in c.read_text(encoding="utf-8")

    def test_idempotent(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, LOT)
        premier = c.read_text(encoding="utf-8")
        enrichir.appliquer(c, LOT)
        # Réappliquer corrige, n'empile pas.
        assert c.read_text(encoding="utf-8") == premier

    def test_sans_affirmation(self, tmp_path):
        # Toutes les fiches n'en portent pas ; en inventer serait pire que rien.
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, {**LOT, "affirmations": []})
        assert enrichir.RIEN in c.read_text(encoding="utf-8")


class TestValidation:
    def test_refuse_sans_theme(self):
        with pytest.raises(enrichir.ErreurLot, match="aucun thème"):
            enrichir.valider("x", {**LOT, "themes": []})

    def test_refuse_phrase_vide(self):
        with pytest.raises(enrichir.ErreurLot, match="phrase"):
            enrichir.valider("x", {**LOT, "phrase": "  "})

    def test_refuse_entite_en_double(self):
        doublon = [{"type": "Institution", "nom": "Assemblée nationale"}] * 2
        with pytest.raises(enrichir.ErreurLot, match="double"):
            enrichir.valider("x", {**LOT, "entites": doublon})

    def test_refuse_libelle_avec_espaces(self):
        # Un libellé mal détouré crée une note de thème distincte, en silence.
        with pytest.raises(enrichir.ErreurLot, match="espaces"):
            enrichir.valider("x", {**LOT, "themes": [" politique"]})

    def test_accepte_un_lot_correct(self):
        enrichir.valider("x", LOT)


class TestTitre:
    def test_remplace_le_titre_generique(self, tmp_path):
        # Instagram ne fournit pas de titre : yt-dlp rend « Video by <compte> »,
        # qui se retrouverait tel quel dans chaque note de thème et d'entité.
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, {**LOT, "titre": "Un vrai titre parlant"})
        t = c.read_text(encoding="utf-8")
        assert "# Un vrai titre parlant" in t
        assert "# Un titre" not in t

    def test_titre_facultatif(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, LOT)
        assert "# Un titre" in c.read_text(encoding="utf-8")


class TestRevueManuelle:
    """Une fiche que le traitement n'a pas pu exploiter reste une vraie fiche,
    mais doit rester retrouvable pour une reprise à la main."""

    def test_theme_non_exploitable_marque_la_fiche(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, {**LOT, "themes": ["non exploitable"]})
        assert mailler.lire_frontmatter(c.read_text(encoding="utf-8"))["statut"] == "a_verifier"

    def test_champ_revue_explicite(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, {**LOT, "revue": True})
        assert mailler.lire_frontmatter(c.read_text(encoding="utf-8"))["statut"] == "a_verifier"

    def test_fiche_normale_reste_enrichie(self, tmp_path):
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, LOT)
        assert mailler.lire_frontmatter(c.read_text(encoding="utf-8"))["statut"] == "enrichi"

    def test_repassage_en_enrichi_si_corrigee(self, tmp_path):
        # Reprise à la main : la fiche redevient exploitable, le statut suit.
        c = _fiche_brute(tmp_path)
        enrichir.appliquer(c, {**LOT, "themes": ["non exploitable"]})
        enrichir.appliquer(c, LOT)
        assert mailler.lire_frontmatter(c.read_text(encoding="utf-8"))["statut"] == "enrichi"
