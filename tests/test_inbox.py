"""Tests de la boîte de réception — le flux continu."""

from reels_graph_md import inbox

URL_A = "https://instagram.com/reel/AAA"
URL_B = "https://instagram.com/reel/BBB"


def _vault(tmp_path, contenu):
    (tmp_path / inbox.NOM_INBOX).write_text(contenu, encoding="utf-8")
    return tmp_path


def _lire(vault, nom):
    chemin = vault / nom
    return chemin.read_text(encoding="utf-8") if chemin.exists() else ""


class TestLectureDeLigne:
    def test_extrait_et_canonicalise(self):
        assert inbox.urls_de_la_ligne(
            "regarde ça https://www.instagram.com/reel/AAA/?igshid=x super"
        ) == [URL_A]

    def test_ignore_ce_qui_n_est_pas_un_post(self):
        assert inbox.urls_de_la_ligne("https://www.instagram.com/moncompte/") == []

    def test_ligne_sans_url(self):
        assert inbox.urls_de_la_ligne("note perso") == []


class TestConsommation:
    def test_archive_ce_qui_est_traite(self, tmp_path):
        vault = _vault(tmp_path, f"{URL_A}\n{URL_B}\n")
        assert inbox.consommer(vault, {URL_A}) == 1
        assert URL_A not in _lire(vault, inbox.NOM_INBOX)
        assert URL_B in _lire(vault, inbox.NOM_INBOX)
        assert URL_A in _lire(vault, inbox.NOM_ARCHIVE)

    def test_une_url_en_echec_reste_en_place(self, tmp_path):
        vault = _vault(tmp_path, f"{URL_B}\n")
        assert inbox.consommer(vault, set()) == 0
        assert URL_B in _lire(vault, inbox.NOM_INBOX)

    def test_survit_a_un_ajout_pendant_le_traitement(self, tmp_path):
        # Le raccourci mobile écrit pendant que le lot tourne : l'URL ajoutée ne
        # doit pas être écrasée par une réécriture depuis l'état initial.
        vault = _vault(tmp_path, f"{URL_A}\n")
        (vault / inbox.NOM_INBOX).write_text(f"{URL_A}\n{URL_B}\n", encoding="utf-8")
        inbox.consommer(vault, {URL_A})
        assert URL_B in _lire(vault, inbox.NOM_INBOX)

    def test_idempotent(self, tmp_path):
        vault = _vault(tmp_path, f"{URL_A}\n")
        inbox.consommer(vault, {URL_A})
        assert inbox.consommer(vault, {URL_A}) == 0
        assert _lire(vault, inbox.NOM_ARCHIVE).count(URL_A) == 1

    def test_lignes_vides_disparaissent_a_la_reecriture(self, tmp_path):
        vault = _vault(tmp_path, f"\n\n{URL_A}\n\n{URL_B}\n\n")
        inbox.consommer(vault, {URL_A})
        assert _lire(vault, inbox.NOM_INBOX) == f"{URL_B}\n"

    def test_pas_de_reecriture_quand_il_n_y_a_rien_a_archiver(self, tmp_path):
        # Écrire pour rien rouvrirait une fenêtre de concurrence avec le
        # raccourci mobile sans aucun bénéfice.
        contenu = f"\n{URL_B}\n"
        vault = _vault(tmp_path, contenu)
        assert inbox.consommer(vault, set()) == 0
        assert _lire(vault, inbox.NOM_INBOX) == contenu

    def test_absence_d_inbox_n_est_pas_une_erreur(self, tmp_path):
        assert inbox.consommer(tmp_path, {URL_A}) == 0

    def test_ligne_a_deux_urls_dont_une_en_echec(self, tmp_path):
        vault = _vault(tmp_path, f"{URL_A} et {URL_B}\n")
        assert inbox.consommer(vault, {URL_A}) == 0
        assert URL_B in _lire(vault, inbox.NOM_INBOX)
