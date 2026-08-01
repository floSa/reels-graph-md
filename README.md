# reels-md

Transforme des reels sauvegardés (Instagram, TikTok, Facebook) en **vault Obsidian**
consultable : une fiche Markdown par reel, la vidéo lisible dans la note, et une
navigation par thème et par entité.

Le problème : plusieurs centaines de reels sauvegardés, dont le contenu est
enfermé dans de la vidéo, donc introuvable. Impossible de retrouver *ce reel qui
parlait du vote à l'Assemblée nationale*.

## Périmètre

**Dans** : métadonnées du post (dont la légende), transcription audio locale,
vidéo conservée, maillage Obsidian.

**Hors** : aucune analyse visuelle. Pas de capture de frames, pas d'OCR, pas de
modèle de vision. Ce qui n'est ni dit à voix haute ni écrit dans la légende
n'entrera pas dans le vault — les fiches concernées sont étiquetées comme telles
plutôt que de laisser croire à un traitement réussi.

## Installation

```bash
uv sync
```

Aucune dépendance Python. Il faut en revanche trois choses sur la machine :

| Outil | Rôle | Installation |
|---|---|---|
| `yt-dlp` | métadonnées + téléchargement | `uv tool install yt-dlp` |
| `ffmpeg` / `ffprobe` | extraction audio | `apt install ffmpeg` |
| serveur Whisper local | transcription | `claude-skills/local-whisper/speaches-up.sh` |

Le moteur de transcription est celui du skill [`watch`](../claude-skills/watch/).
Il est importé depuis son emplacement réel, pas recopié. Si claude-skills est
ailleurs :

```bash
export REELS_MD_WATCH_SCRIPTS=/chemin/vers/watch/scripts
```

## Étape 0 — récupérer ses reels sauvegardés

Aucune plateforme n'expose d'API pour les contenus sauvegardés. Le seul chemin
fiable est l'export officiel des données. C'est manuel et asynchrone (quelques
heures à quelques jours), et ça se fait une fois.

| Plateforme | Chemin | Fichier attendu |
|---|---|---|
| Instagram | Centre des comptes → Vos informations et autorisations → Télécharger vos informations → **JSON** | `saved_posts.json` |
| TikTok | Paramètres → Compte → Télécharger vos données → *Custom data* → **Likes and Favorites** → JSON | `user_data_tiktok.json` |
| Facebook | Paramètres → Vos informations Facebook → Télécharger vos informations → JSON | *Éléments enregistrés et collections* |

TikTok distingue **Favoris** (le signet — ce qu'on veut) et **J'aime** (autre
volume, beaucoup moins pertinent).

Le format des fichiers n'a aucune importance : ils sont lus en texte brut et
attaqués à la regex. txt, csv, json ou html, un seul code les lit tous.

## Usage

```bash
# voir ce qui serait traité, sans rien télécharger
uv run reels-ingest exports/*.json --vault ~/Vault --lister

# tester sur 10 reels avant d'en lancer 300
uv run reels-ingest exports/*.json --vault ~/Vault --cookies firefox --limite 10

# puis le maillage, après l'enrichissement des fiches
uv run reels-mailler --vault ~/Vault
```

Le script **reprend où il s'est arrêté**. On peut le couper à tout moment : le
journal est réécrit après chaque reel. Relancer la même commande retente
uniquement ce qui a échoué.

### Cookies

Instagram et Facebook les exigent. Deux pièges sans contournement :

- **Firefox obligatoire.** Chrome 127+ chiffre ses cookies d'une façon que yt-dlp
  ne sait pas déchiffrer sous Windows.
- **Navigateur complètement fermé** pendant le script : il verrouille son fichier
  de cookies.

## Le vault produit

```
Vault/
├── fiches/     insta_DXabc123.md        une fiche par reel
├── reels/      insta_DXabc123.mp4       la vidéo, conservée
├── themes/     politique.md             généré, wikilinks
├── entites/    Assemblée nationale.md   généré, wikilinks
└── journal.json
```

La vidéo est conservée délibérément : c'est elle qui permet de revoir le reel
depuis Obsidian même quand le post d'origine a disparu — ce qui arrive à environ
un tiers d'un stock ancien. Compter 1 à 3 Go pour 300 reels.

Sur les horodatages : contrairement à YouTube, Instagram, TikTok et Facebook
n'honorent pas de paramètre `?t=` dans leurs URLs. Les repères `[MM:SS]` renvoient
donc à la vidéo locale embarquée en tête de fiche, pas au post d'origine.

## Le pipeline

| # | Étape | Automatique |
|---|---|---|
| 1 | Extraction des liens depuis les exports | oui |
| 2 | Filtrage par le journal | oui |
| 3 | Métadonnées (`yt-dlp --dump-json`) | oui |
| 4 | Téléchargement de la vidéo, **une seule passe** | oui |
| 5 | Extraction audio locale (ffmpeg) | oui |
| 6 | Transcription Whisper, **langue forcée** | oui |
| 7 | Écriture de la fiche | oui |
| 8 | Synthèse, thèmes, entités | **Claude, par lots** |
| 9 | Maillage Obsidian (`reels-mailler`) | oui |

Les étapes 1 à 7 tournent sans personne. L'étape 8 est la seule qui consomme du
quota. L'étape 9 est du texte, instantanée.

### Règle éditoriale de l'étape 8

Séparation stricte entre **ce que dit le reel** et **ce qui est établi**. Style
indirect obligatoire (« le reel affirme que… »), jamais de voix assertive. Sur du
contenu politique, une synthèse neutre en apparence qui reprend une affirmation
militante est un défaut, pas un détail. Une fiche trop pauvre pour un vrai résumé
doit être signalée comme telle, pas comblée.

Les thèmes sont **émergents** : aucune liste prédéfinie, ils se déduisent de ce
qui est lu, en réutilisant les mêmes libellés d'une fiche à l'autre.

## Ce qu'on doit au voisinage

- **[sosoj92/reels-vault](https://github.com/sosoj92/reels-vault)** (MIT) — la
  couche batch : lecture des exports à la regex sans jamais les parser, journal
  de reprise, gestion des cookies, taxonomie émergente. Trois de ses fragilités
  sont corrigées ici : les codes de retour des sous-processus sont vérifiés, les
  identifiants de fichier sont stables (`hash()` est randomisé par processus en
  Python 3), et les URLs sont canonicalisées avant de servir de clé.
- **`watch` / `watch-md`** (claude-skills) — le moteur de transcription et la
  doctrine éditoriale.

## Tests

```bash
uv run pytest
```

Les tests couvrent les fonctions pures : extraction et normalisation des liens,
échappement YAML, évaluation de fiabilité, maillage et son idempotence. Les
étapes réseau ne sont pas testées automatiquement.

## Limites connues

- **Un reel sans voix off produit une fiche vide.** Ce n'est pas de la magie,
  c'est de la transcription. D'où le `--limite 10` avant de lancer le stock.
- **Les carrousels photo** n'ont ni audio ni transcript : la fiche se réduit à la
  légende, et porte `fiabilite: legende_seule`.
- **Les sous-titres de plateforme** sont rares sur Instagram, parfois présents sur
  TikTok. Quand ils existent, ils sont conservés comme seconde source à croiser —
  mais on ne peut pas compter dessus.
- **Instagram rate-limite sévèrement** : procéder par lots de ~50 étalés sur
  plusieurs jours.
- **La recherche sémantique n'est pas encore là.** La navigation par thème et par
  entité fonctionne ; retrouver un reel à partir d'une question en langage naturel
  reste à concevoir.
