"""Extraction des liens de reels depuis les exports de données des plateformes.

Le principe repris de reels-vault : les fichiers d'export ne sont **jamais**
parsés comme du JSON. Ils sont lus en texte brut et attaqués à la regex. Un seul
code lit donc les trois exports (Instagram, TikTok, Facebook) quel que soit leur
format — txt, csv, json, html — sans un octet de code spécifique par plateforme.

On ajoute deux choses que reels-vault n'a pas :

1. **Un filtre de contenu.** Un export Facebook contient des centaines d'URLs
   qui ne sont pas des reels (profils, groupes, paramètres). Sans filtre, chacune
   part au téléchargement et échoue. On ne garde que les formes d'URL qui
   désignent un post.
2. **Une normalisation.** reels-vault garde l'URL brute comme clé de journal mais
   dérive le nom de fichier d'une URL tronquée : deux variantes de la même URL
   (`?igshid=…`, `?utm_source=…`) produisent deux entrées de journal mais un
   seul nom de fichier, donc la seconde écrase la fiche de la première. Ici tout
   part de la même forme canonique.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

# Large volontairement : on ratisse tout ce qui ressemble à un lien de
# plateforme, le tri fin est fait ensuite par `est_contenu()`.
MOTIF_LIEN = re.compile(
    r"https?://(?:[\w-]+\.)*"
    r"(?:tiktok\.com|instagram\.com|facebook\.com|fb\.watch|fb\.me)"
    r"/[^\s\"'<>,\)\]}\\]+",
    re.IGNORECASE,
)

# Ponctuation collée en fin d'URL quand elle est extraite d'une phrase ou d'un
# champ JSON échappé.
FIN_PARASITE = ".,;:!?'\"»)]}"

PLATEFORMES = {
    "tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "fb.watch": "facebook",
    "fb.me": "facebook",
}

# Formes d'URL qui désignent un contenu publiable, par plateforme.
#
# Rien de générique ici : un motif large du type `^/[A-Za-z0-9]{6,}$` attraperait
# `/marketplace`, `/explore` ou `/settings`. Les liens courts, dont le code est
# justement opaque, sont traités à part dans `est_contenu()` en s'appuyant sur
# l'hôte — c'est lui qui garantit que le chemin est un identifiant de post.
MOTIFS_CONTENU = {
    "instagram": (
        re.compile(r"^/(?:p|reel|reels|tv)/[\w-]+"),
        re.compile(r"^/[\w.]+/(?:p|reel|reels|tv)/[\w-]+"),  # forme /<compte>/reel/<code>
    ),
    "tiktok": (
        re.compile(r"^/@[\w.-]+/(?:video|photo)/\d+"),
        re.compile(r"^/t/[A-Za-z0-9]+"),
        re.compile(r"^/v/\d+"),
    ),
    "facebook": (
        re.compile(r"^/reel/\d+"),
        re.compile(r"^/[\w.-]+/videos/\d+"),
        re.compile(r"^/videos/\d+"),
        re.compile(r"^/share/[rvp]/[\w-]+"),
        re.compile(r"^/story\.php$"),
        re.compile(r"^/video\.php$"),
    ),
}

# Hôtes de raccourcissement : tout chemin non vide y est un identifiant de post.
HOTES_COURTS = re.compile(
    r"^(?:vm\.tiktok\.com|vt\.tiktok\.com|fb\.watch|fb\.me)$", re.IGNORECASE
)

# Paramètres de query à conserver : tout le reste est du tracking qui fait
# diverger deux URLs pointant le même post.
PARAMS_UTILES = {"v"}

SOUS_DOMAINES_IGNORES = {"www", "m", "web", "l", "fr-fr", "fr"}


def plateforme_de(url: str) -> str | None:
    """Renvoie 'instagram' | 'tiktok' | 'facebook', ou None si hors périmètre."""
    hote = urlsplit(url).netloc.lower().split(":")[0]
    for domaine, nom in PLATEFORMES.items():
        if hote == domaine or hote.endswith("." + domaine):
            return nom
    return None


def normaliser(url: str) -> str:
    """Forme canonique d'une URL : c'est elle qui sert de clé partout.

    Minuscule sur le schéma et l'hôte, sous-domaines cosmétiques retirés,
    paramètres de tracking supprimés, slash final retiré. Deux liens vers le même
    post convergent ici, ce qui rend le journal et les noms de fichiers cohérents.
    """
    parts = urlsplit(url.strip().rstrip(FIN_PARASITE))

    hote = parts.netloc.lower().split(":")[0]
    morceaux = hote.split(".")
    # On ne retire un préfixe que s'il reste un domaine complet derrière, pour ne
    # pas amputer `vm.tiktok.com` (vm. porte la redirection, il est significatif).
    if len(morceaux) > 2 and morceaux[0] in SOUS_DOMAINES_IGNORES:
        hote = ".".join(morceaux[1:])

    chemin = parts.path.rstrip("/") or "/"

    query = ""
    if parts.query:
        gardes = {
            cle: valeurs[0]
            for cle, valeurs in parse_qs(parts.query).items()
            if cle.lower() in PARAMS_UTILES and valeurs
        }
        query = "&".join(f"{c}={v}" for c, v in sorted(gardes.items()))

    base = f"https://{hote}{chemin}"
    return f"{base}?{query}" if query else base


def est_contenu(url: str) -> bool:
    """True si l'URL désigne un post, pas un profil ou une page de réglages.

    C'est le filtre qui rend un export Facebook exploitable : il est rempli de
    liens vers des profils, des groupes et des pages de réglages qui partiraient
    sinon au téléchargement pour échouer un par un.
    """
    nom = plateforme_de(url)
    if nom is None:
        return False

    parts = urlsplit(normaliser(url))
    chemin = parts.path

    # Lien court : c'est l'hôte qui atteste du contenu, le code est opaque.
    if HOTES_COURTS.match(parts.netloc):
        return len(chemin.strip("/")) >= 4

    # /watch n'est un contenu que porteur d'un ?v=
    if nom == "facebook" and chemin.rstrip("/") in ("", "/watch"):
        return parts.query.startswith("v=")

    return any(motif.match(chemin) for motif in MOTIFS_CONTENU[nom])


def identifiant(url: str) -> str:
    """Nom de fichier court, sûr et **stable** dérivé de l'URL canonique.

    Stable est le mot important : reels-vault utilise `hash()` en repli, or
    `hash()` sur une chaîne est randomisé par processus en Python 3. Le nom
    changeait donc à chaque exécution. On utilise un sha1 tronqué.
    """
    canonique = normaliser(url)
    nom = plateforme_de(canonique) or "inconnu"
    prefixe = {"instagram": "insta", "tiktok": "tiktok", "facebook": "fb"}.get(nom, nom)

    parts = urlsplit(canonique)
    # Le `v=` prime sur le chemin : sur `/watch?v=123`, le dernier segment est
    # « watch », qui ferait collisionner *tous* les liens Facebook de ce type sur
    # un seul nom de fichier.
    slug = parse_qs(parts.query).get("v", [""])[0] if parts.query else ""
    if not slug:
        slug = parts.path.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^A-Za-z0-9_-]", "", slug)[:40]

    if not slug:
        slug = hashlib.sha1(canonique.encode("utf-8")).hexdigest()[:12]

    return f"{prefixe}_{slug}"


def extraire(chemin: Path | str) -> list[str]:
    """Toutes les URLs de contenu d'un fichier d'export, canoniques et dédoublonnées.

    L'ordre d'apparition est conservé : sur un export chronologique, on traite les
    reels les plus anciens d'abord, ce qui rend une reprise partielle lisible.
    """
    texte = Path(chemin).read_text(encoding="utf-8", errors="ignore")
    liens: list[str] = []
    vus: set[str] = set()

    for brut in MOTIF_LIEN.findall(texte):
        brut = brut.rstrip(FIN_PARASITE)
        if not est_contenu(brut):
            continue
        canonique = normaliser(brut)
        if canonique not in vus:
            vus.add(canonique)
            liens.append(canonique)

    return liens


def extraire_plusieurs(chemins: list[Path | str]) -> list[str]:
    """Fusionne plusieurs exports (un par plateforme) en une seule liste dédoublonnée."""
    liens: list[str] = []
    vus: set[str] = set()
    for chemin in chemins:
        for lien in extraire(chemin):
            if lien not in vus:
                vus.add(lien)
                liens.append(lien)
    return liens
