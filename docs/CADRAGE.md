# Cadrage — reels-graph-md

Le **POURQUOI**. Le **COMMENT** est dans [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 1. Pitch

Plusieurs centaines de reels sauvegardés sur Instagram, TikTok et Facebook. Le
contenu informatif qu'ils portent est enfermé dans de la vidéo, donc introuvable :
impossible de retrouver *ce reel qui parlait du vote à l'Assemblée nationale*.

Le projet en fait un vault Obsidian consultable. Trois capacités :

1. **Récolter et transcrire** — de l'export officiel de plateforme jusqu'à une
   fiche Markdown par reel, transcription audio locale comprise, sans intervention.
2. **Archiver durablement** — la vidéo est conservée dans le vault et lisible dans
   la note, même quand le post d'origine a disparu.
3. **Naviguer** — un maillage par thème et par entité citée, pour passer d'un reel
   à l'autre et retrouver tout ce qui parle d'un sujet donné.

Cas d'usage visé : du contenu **informatif**, en particulier politique. Retrouver
un chiffre avancé, savoir qui l'a dit et quand, et pouvoir citer la source.

---

## 2. Objectifs et périmètre

**Dans le périmètre (V1)**

- Trois plateformes : Instagram, TikTok, Facebook.
- Récolte depuis les exports officiels de données, plus un flux continu par
  fichier `inbox.txt`.
- Transcription audio **locale**, langue forcée.
- Conservation de la vidéo dans le vault.
- Fiche Markdown avec frontmatter exploitable par Obsidian et Dataview.
- Maillage par thème **et par entité**.
- Reprise après interruption sur un stock de plusieurs centaines d'éléments.

**Hors périmètre (V1)**

- **Toute analyse visuelle** : pas de capture de frames, pas d'OCR, pas de modèle
  de vision. Décision explicite, prise après analyse : c'était le poste le plus
  coûteux et le plus incertain, pour un gain incertain sur ce corpus.
- Traitement des carrousels photo au-delà de leur légende — conséquence directe du
  point précédent.
- Recherche sémantique en langage naturel, voir §6.
- Toute interface : le client est Obsidian.
- Toute automatisation du contournement de rate-limit ou d'authentification.

---

## 3. Contraintes (fermes)

| Contrainte | Détail |
|---|---|
| Coût | Zéro clé d'API payante. La transcription tourne en local. |
| Confidentialité | Le contenu des reels ne quitte pas la machine. |
| Dépendances | Aucune dépendance Python de production. Binaires externes uniquement. |
| Licences | Open-source uniquement. |
| Environnement | Python 3.12 géré par uv. Machine de développement personnelle, GPU disponible mais non requis. |
| Légalité | Aucun contournement de protection ni de rate-limit ; uniquement les exports officiels et les cookies de l'utilisateur. |

---

## 4. Hypothèses

- **Le contenu visé est parlé.** Le corpus est du contenu informatif, où l'essentiel
  passe par la voix off. Ce qui la remettrait en cause : un taux élevé de fiches
  `vide` ou `legende_seule` sur un lot de test — d'où l'obligation de tester sur 10
  reels avant d'en lancer 300.

- **La légende porte de l'information vérifiable.** Sur du contenu informatif, elle
  contient souvent les liens, les noms complets et les sources. Elle est donc
  conservée **en verbatim**, jamais résumée.

- **Les exports officiels restent disponibles et exploitables.** Aucune plateforme
  n'expose d'API pour les contenus sauvegardés ; l'export est le seul chemin. Sa
  suppression ou un changement de format casserait l'étape 0. Le choix de lire les
  fichiers en texte brut plutôt que de les parser limite l'exposition à ce risque.

- **Un tiers du stock ancien est irrécupérable.** Posts supprimés ou passés en
  privé. C'est ce qui justifie de conserver les vidéos plutôt que les liens.

- **La cohérence des thèmes repose sur la mémoire de session du LLM.** Aucune
  taxonomie n'est imposée. Un traitement dispersé sur trop de sessions produirait
  des libellés divergents pour un même thème.

---

## 5. Stack technique

| Brique | Choix | Licence |
|---|---|---|
| Langage | Python 3.12 | PSF |
| Environnement | uv | MIT / Apache-2.0 |
| Build | hatchling | MIT |
| Tests | pytest | MIT |
| Téléchargement | yt-dlp | Unlicense |
| Traitement média | ffmpeg | LGPL-2.1+ / GPL selon le build |
| Transcription | faster-whisper (CTranslate2) via speaches | MIT |
| Modèle | Whisper large-v3 / large-v3-turbo | MIT (poids) |
| Lecture du vault | Obsidian | propriétaire, gratuit pour usage personnel |
| Ce projet | Code applicatif | MIT — Copyright (c) 2026 floSa (fichier `LICENSE` **à ajouter**) |

Basé sur les idées de [sosoj92/reels-vault](https://github.com/sosoj92/reels-vault)
(MIT) pour la couche batch, et sur le skill `watch` (MIT, dérivé de
[claude-video](https://github.com/bradautomates/claude-video)) pour le moteur de
transcription.

---

## 6. Décisions

**Décisions figées**

- **Pas d'analyse visuelle** plutôt qu'une détection de cartons de texte, parce que
  le portage de la détection de slides au format court vertical était le poste le
  plus coûteux du projet, pour un bénéfice incertain sur du contenu parlé.
- **Vidéo conservée** plutôt que lien seul, parce qu'un tiers du stock ancien
  disparaît et qu'un lien mort ne peut pas servir de source.
- **Whisper local** plutôt qu'une API hébergée, parce que le coût doit rester nul
  et que le contenu ne doit pas sortir de la machine.
- **Taxonomie émergente** plutôt qu'une liste de thèmes prédéfinie, parce qu'une
  liste imposée fait entrer le corpus dans des cases décidées d'avance ; en la
  laissant émerger, on découvre ce qui est réellement sauvegardé.
- **Séparation stricte entre ce que dit le reel et ce qui est établi.** Style
  indirect obligatoire dans les synthèses. Sur du contenu politique, une synthèse
  d'apparence neutre qui reprend une affirmation militante est un défaut, pas un
  détail.
- **Étiqueter plutôt que combler.** Une fiche sans contenu parlé porte
  `fiabilite: vide` ou `legende_seule`. Une fiche trop pauvre pour un vrai résumé
  doit être signalée comme telle.

**À trancher**

- **La couche de recherche.** Deux options :
  - *Obsidian seul* — notes de thème et d'entité, recherche native. Déjà
    implémenté, coût nul. Navigation plutôt que requête ; la recherche native
    étant littérale, elle ne relie pas « vote à l'Assemblée nationale » à un reel
    qui dit « les députés ont adopté ».
  - *Couche sémantique* — index d'embeddings local ou graphe de connaissance.
    Répond mieux à « je pose une question, je récupère les reels », mais demande
    de la conception.

  Recommandation par défaut : mesurer d'abord la couverture réelle du maillage par
  entités sur un vrai lot, puis décider. La couche sémantique ne se justifie que si
  la navigation se révèle insuffisante.

- **Le fichier `LICENSE`.** Le dépôt est public et n'en a pas. MIT est la licence
  par défaut du reste des projets ; à confirmer explicitement avant ajout.

---

## 7. Roadmap

0. **Socle** — extraction des liens, journal, téléchargement, transcription,
   fiche, maillage. *Fait.*
1. **Validation réseau** — un lot de 10 reels par plateforme, avec cookies.
   Confronter le filtre d'URL à un export Facebook réel. *Bloquant pour la suite.*
2. **Outillage de l'enrichissement** — procédure de traitement par lots, avec la
   règle éditoriale et la contrainte de cohérence des libellés.
3. **Passage à l'échelle** — lots de ~50 étalés, mesure du taux d'échec et de la
   durée par reel.
4. **Recherche** — trancher §6 sur la base des mesures de l'étape 3.
5. **Flux continu** — raccourci de partage mobile vers `inbox.txt` et déclenchement
   périodique.

---

## 8. Stratégie de tests

**Ce qui est couvert** — 39 tests unitaires sur les fonctions pures, exécutés par
`uv run pytest` :

| Domaine | Ce qu'on prouve |
|---|---|
| Extraction de liens | Les trois plateformes sont reconnues, un domaine qui finit pareil ne passe pas, le bruit des exports est écarté |
| Normalisation | Deux variantes d'une même URL convergent, les sous-domaines significatifs survivent |
| Identifiant | Stable entre deux exécutions, insensible au tracking, sans collision sur `/watch?v=` |
| Échappement YAML | Une légende avec `:` et guillemets ne casse pas le frontmatter |
| Fiabilité | Les quatre niveaux sont attribués correctement |
| Maillage | Les wikilinks sont posés, l'opération est idempotente, une fiche non enrichie est ignorée |

**Ce qui n'est pas couvert** — les étapes réseau et le serveur Whisper. Elles ont
été validées **manuellement**, de bout en bout, sur un fichier audio public :
téléchargement, extraction ffmpeg, transcription, transcript horodaté. Le chemin
propre aux trois plateformes reste à valider avec des cookies réels.

Deux défauts ont été trouvés par ces tests pendant la construction : une collision
d'identifiants sur les liens Facebook `/watch?v=`, et une recherche de fichier
téléchargé trop étroite qui signalait un échec sans dire ce qui existait.

---

## 9. Références

- [sosoj92/reels-vault](https://github.com/sosoj92/reels-vault) — la couche batch
  et son retour d'expérience de terrain (cookies, rate-limit, taux de perte).
- Skill `watch` / `watch-md` (dépôt `claude-skills`) — moteur de transcription et
  doctrine éditoriale.
- [claude-video](https://github.com/bradautomates/claude-video) — projet amont dont
  `watch` dérive.
- [speaches](https://github.com/speaches-ai/speaches) — serveur Whisper local
  compatible OpenAI.
