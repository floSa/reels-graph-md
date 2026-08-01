"""Tests de l'extraction de liens — la brique la plus facile à casser en silence."""

from reels_md import liens


class TestPlateforme:
    def test_reconnait_les_trois(self):
        assert liens.plateforme_de("https://www.instagram.com/reel/ABC/") == "instagram"
        assert liens.plateforme_de("https://vm.tiktok.com/ZGabc/") == "tiktok"
        assert liens.plateforme_de("https://fb.watch/xyz123/") == "facebook"

    def test_ignore_le_reste(self):
        assert liens.plateforme_de("https://youtube.com/watch?v=1") is None

    def test_ne_matche_pas_un_domaine_qui_finit_pareil(self):
        # notinstagram.com ne doit pas passer pour instagram.com
        assert liens.plateforme_de("https://notinstagram.com/reel/A/") is None


class TestNormalisation:
    def test_supprime_le_tracking(self):
        a = liens.normaliser("https://www.instagram.com/reel/ABC/?igshid=xyz")
        b = liens.normaliser("https://instagram.com/reel/ABC?utm_source=ig_web")
        assert a == b == "https://instagram.com/reel/ABC"

    def test_garde_le_v_de_facebook(self):
        assert (
            liens.normaliser("https://www.facebook.com/watch/?v=123&ref=share")
            == "https://facebook.com/watch?v=123"
        )

    def test_preserve_les_sous_domaines_significatifs(self):
        # vm. porte la redirection : l'amputer casserait le lien
        assert liens.normaliser("https://vm.tiktok.com/ZGabc/") == "https://vm.tiktok.com/ZGabc"

    def test_retire_la_ponctuation_de_fin(self):
        assert liens.normaliser("https://instagram.com/reel/ABC/.") == "https://instagram.com/reel/ABC"


class TestEstContenu:
    def test_accepte_les_posts(self):
        for url in [
            "https://www.instagram.com/reel/DXabc123/",
            "https://www.instagram.com/p/DXabc123/",
            "https://www.tiktok.com/@user.name/video/7412345678901234567",
            "https://vm.tiktok.com/ZGeabcdef/",
            "https://www.facebook.com/reel/1234567890",
            "https://www.facebook.com/watch/?v=1234567890",
            "https://fb.watch/aBc12dEf/",
        ]:
            assert liens.est_contenu(url), url

    def test_rejette_le_bruit_des_exports(self):
        for url in [
            "https://www.instagram.com/nomducompte/",
            "https://www.instagram.com/accounts/login/",
            "https://www.tiktok.com/@user.name",
            "https://www.tiktok.com/explore",
            "https://www.tiktok.com/foryou",
            "https://www.facebook.com/marketplace",
            "https://www.facebook.com/settings",
            "https://www.facebook.com/groups/123456",
            "https://www.facebook.com/watch",
        ]:
            assert not liens.est_contenu(url), url


class TestIdentifiant:
    def test_stable_entre_deux_appels(self):
        url = "https://www.facebook.com/share/r/abcDEF/"
        assert liens.identifiant(url) == liens.identifiant(url)

    def test_insensible_au_tracking(self):
        a = liens.identifiant("https://www.instagram.com/reel/ABC/?igshid=1")
        b = liens.identifiant("https://instagram.com/reel/ABC")
        assert a == b == "insta_ABC"

    def test_prefixe_par_plateforme(self):
        assert liens.identifiant("https://www.tiktok.com/@u/video/74123").startswith("tiktok_")
        assert liens.identifiant("https://www.facebook.com/reel/74123").startswith("fb_")

    def test_utilise_le_v_quand_le_chemin_est_vide(self):
        assert liens.identifiant("https://www.facebook.com/watch/?v=998877") == "fb_998877"


class TestExtraction:
    def test_lit_un_export_json_sans_le_parser(self, tmp_path):
        # Forme réelle d'un saved_posts.json Instagram : URL noyée dans du JSON
        # échappé. On ne parse rien, on ratisse.
        export = tmp_path / "saved_posts.json"
        export.write_text(
            '{"saved_saved_media":[{"title":"compte",'
            '"string_map_data":{"Enregistr\\u00e9 le":'
            '{"href":"https://www.instagram.com/reel/DXabc123/","timestamp":1}}}]}',
            encoding="utf-8",
        )
        assert liens.extraire(export) == ["https://instagram.com/reel/DXabc123"]

    def test_dedoublonne_les_variantes(self, tmp_path):
        fichier = tmp_path / "liens.txt"
        fichier.write_text(
            "https://www.instagram.com/reel/ABC/?igshid=1\n"
            "https://instagram.com/reel/ABC\n"
            "https://www.instagram.com/reel/ABC/\n",
            encoding="utf-8",
        )
        assert liens.extraire(fichier) == ["https://instagram.com/reel/ABC"]

    def test_filtre_le_bruit(self, tmp_path):
        fichier = tmp_path / "export.txt"
        fichier.write_text(
            "https://www.facebook.com/marketplace/item/1\n"
            "https://www.facebook.com/reel/999\n"
            "https://youtube.com/watch?v=zzz\n",
            encoding="utf-8",
        )
        assert liens.extraire(fichier) == ["https://facebook.com/reel/999"]

    def test_conserve_l_ordre(self, tmp_path):
        fichier = tmp_path / "liens.txt"
        fichier.write_text(
            "https://instagram.com/reel/B/\nhttps://instagram.com/reel/A/\n",
            encoding="utf-8",
        )
        assert liens.extraire(fichier) == [
            "https://instagram.com/reel/B",
            "https://instagram.com/reel/A",
        ]

    def test_fusionne_plusieurs_exports(self, tmp_path):
        a = tmp_path / "insta.json"
        a.write_text("https://instagram.com/reel/A/", encoding="utf-8")
        b = tmp_path / "tiktok.json"
        b.write_text("https://www.tiktok.com/@u/video/7412345678901234567", encoding="utf-8")
        resultat = liens.extraire_plusieurs([a, b])
        assert len(resultat) == 2
