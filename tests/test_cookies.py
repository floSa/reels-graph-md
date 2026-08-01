"""Tests de la résolution des cookies — le piège WSL.

`--cookies-from-browser firefox` ne cherche que dans les emplacements Linux.
Sous WSL, le navigateur tourne côté Windows : yt-dlp échoue alors avec
« could not find firefox cookies database », message qui n'oriente vers aucune
solution. La résolution va chercher le profil Windows elle-même.
"""

from pathlib import Path

from reels_graph_md.ytdlp import resoudre_cookies


def _profil(tmp_path, nom="naw7fadr.default-release"):
    profil = tmp_path / nom
    profil.mkdir(parents=True)
    (profil / "cookies.sqlite").write_bytes(b"")
    return profil


class TestFichierCookiesTxt:
    def test_chemin_de_fichier_existant(self, tmp_path):
        fichier = tmp_path / "cookies.txt"
        fichier.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
        args, message = resoudre_cookies(
            str(fichier), profil_linux=False, profils_windows=[]
        )
        assert args == ["--cookies", str(fichier.resolve())]
        assert message is None


class TestDossierDeProfil:
    def test_dossier_de_profil_direct(self, tmp_path):
        profil = _profil(tmp_path)
        args, _ = resoudre_cookies(str(profil), profil_linux=False, profils_windows=[])
        assert args == ["--cookies-from-browser", f"firefox:{profil}"]

    def test_dossier_sans_base_de_cookies_n_est_pas_un_profil(self, tmp_path):
        vide = tmp_path / "vide"
        vide.mkdir()
        args, _ = resoudre_cookies(str(vide), profil_linux=False, profils_windows=[])
        assert args[0] == "--cookies-from-browser"
        assert args[1] == str(vide)


class TestNomDeNavigateur:
    def test_linux_avec_profil_natif(self, tmp_path):
        # Cas normal hors WSL : on laisse yt-dlp se débrouiller.
        args, message = resoudre_cookies(
            "firefox", profil_linux=True, profils_windows=[_profil(tmp_path)]
        )
        assert args == ["--cookies-from-browser", "firefox"]
        assert message is None

    def test_wsl_bascule_sur_le_profil_windows(self, tmp_path):
        profil = _profil(tmp_path)
        args, message = resoudre_cookies(
            "firefox", profil_linux=False, profils_windows=[profil]
        )
        assert args == ["--cookies-from-browser", f"firefox:{profil}"]
        assert message and str(profil) in message

    def test_wsl_retient_le_premier_profil_propose(self, tmp_path):
        # L'appelant trie par fraîcheur des cookies : on respecte cet ordre.
        recent = _profil(tmp_path, "recent")
        ancien = _profil(tmp_path, "ancien")
        args, _ = resoudre_cookies(
            "firefox", profil_linux=False, profils_windows=[recent, ancien]
        )
        assert args[1] == f"firefox:{recent}"

    def test_sans_profil_windows_on_ne_bricole_pas(self):
        args, message = resoudre_cookies(
            "firefox", profil_linux=False, profils_windows=[]
        )
        assert args == ["--cookies-from-browser", "firefox"]
        assert message is None

    def test_autre_navigateur_non_touche(self, tmp_path):
        # La bascule ne vaut que pour Firefox : Chrome chiffre ses cookies sous
        # Windows et yt-dlp ne saurait pas les déchiffrer depuis WSL.
        args, _ = resoudre_cookies(
            "chrome", profil_linux=False, profils_windows=[_profil(tmp_path)]
        )
        assert args == ["--cookies-from-browser", "chrome"]

    def test_forme_explicite_respectee(self):
        args, message = resoudre_cookies(
            "firefox:/un/chemin", profil_linux=False, profils_windows=[Path("/autre")]
        )
        assert args == ["--cookies-from-browser", "firefox:/un/chemin"]
        assert message is None
