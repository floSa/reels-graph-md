"""Tests du journal — reprise et déduplication sur l'identifiant natif."""

from reels_graph_md.journal import Journal


def _journal(tmp_path):
    return Journal(tmp_path / "journal.json")


class TestReprise:
    def test_ok_est_saute_echec_est_retente(self, tmp_path):
        j = _journal(tmp_path)
        j.succes("https://instagram.com/reel/A", fiche="insta_A.md")
        j.echec("https://instagram.com/reel/B", "429")
        restant = j.a_traiter(
            ["https://instagram.com/reel/A", "https://instagram.com/reel/B"]
        )
        assert restant == ["https://instagram.com/reel/B"]

    def test_compte_les_tentatives(self, tmp_path):
        j = _journal(tmp_path)
        j.echec("https://instagram.com/reel/B", "429")
        j.echec("https://instagram.com/reel/B", "429")
        assert j.entrees["https://instagram.com/reel/B"]["tentatives"] == 2

    def test_persiste_et_se_recharge(self, tmp_path):
        _journal(tmp_path).succes("https://instagram.com/reel/A", fiche="insta_A.md")
        assert _journal(tmp_path).est_fait("https://instagram.com/reel/A")

    def test_journal_corrompu_ne_bloque_pas(self, tmp_path):
        (tmp_path / "journal.json").write_text("{ceci n'est pas du json", encoding="utf-8")
        assert _journal(tmp_path).entrees == {}


class TestDedupNative:
    """La canonicalisation d'URL ne peut pas rapprocher un lien court de sa forme
    résolue : seule la plateforme sait qu'il s'agit du même reel."""

    COURT = "https://vm.tiktok.com/ZGabc"
    LONG = "https://tiktok.com/@compte/video/7412345678901234567"
    NATIF = "tiktok:7412345678901234567"

    def test_retrouve_l_url_deja_traitee(self, tmp_path):
        j = _journal(tmp_path)
        j.succes(self.COURT, fiche="tiktok_ZGabc.md", natif=self.NATIF)
        assert j.url_pour_natif(self.NATIF) == self.COURT

    def test_index_survit_au_rechargement(self, tmp_path):
        _journal(tmp_path).succes(self.COURT, fiche="x.md", natif=self.NATIF)
        assert _journal(tmp_path).url_pour_natif(self.NATIF) == self.COURT

    def test_un_alias_ne_devient_pas_la_reference(self, tmp_path):
        # Sinon l'alias remplacerait l'original dans l'index et la fiche pointée
        # deviendrait une chaîne vide au doublon suivant.
        j = _journal(tmp_path)
        j.succes(self.COURT, fiche="tiktok_ZGabc.md", natif=self.NATIF)
        j.succes(self.LONG, natif=self.NATIF, alias_de=self.COURT)
        assert j.url_pour_natif(self.NATIF) == self.COURT
        assert _journal(tmp_path).url_pour_natif(self.NATIF) == self.COURT

    def test_natif_inconnu(self, tmp_path):
        assert _journal(tmp_path).url_pour_natif("tiktok:999") is None

    def test_un_echec_ne_pollue_pas_l_index(self, tmp_path):
        j = _journal(tmp_path)
        j.echec(self.COURT, "post supprimé")
        assert j.url_pour_natif(self.NATIF) is None


class TestResume:
    def test_compte_par_statut(self, tmp_path):
        j = _journal(tmp_path)
        j.succes("https://instagram.com/reel/A", fiche="a.md")
        j.succes("https://instagram.com/reel/B", fiche="b.md")
        j.echec("https://instagram.com/reel/C", "boum")
        assert j.resume() == {"ok": 2, "echec": 1, "impossible": 0}


class TestImpossible:
    """Un troisième état, distinct de l'échec : structurel, donc jamais retenté."""

    URL = "https://instagram.com/p/DbJci7QEQF5"

    def test_sort_de_la_file(self, tmp_path):
        j = _journal(tmp_path)
        j.impossible(self.URL, "carrousel photo — aucune donnée exploitable")
        assert j.a_traiter([self.URL]) == []

    def test_survit_au_rechargement(self, tmp_path):
        _journal(tmp_path).impossible(self.URL, "carrousel photo")
        assert _journal(tmp_path).a_traiter([self.URL]) == []

    def test_compte_a_part(self, tmp_path):
        j = _journal(tmp_path)
        j.impossible(self.URL, "carrousel photo")
        j.echec("https://instagram.com/reel/B", "429")
        assert j.resume() == {"ok": 0, "echec": 1, "impossible": 1}

    def test_un_echec_reste_retente(self, tmp_path):
        # La distinction est tout l'intérêt : transitoire contre structurel.
        j = _journal(tmp_path)
        j.echec("https://instagram.com/reel/B", "429")
        assert j.a_traiter(["https://instagram.com/reel/B"]) == ["https://instagram.com/reel/B"]
