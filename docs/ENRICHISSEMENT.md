# Enrichissement — l'étape 8

La seule étape du pipeline qui ne s'automatise pas. Les étapes 1 à 7 produisent
des fiches **brutes** : métadonnées, légende verbatim, transcript horodaté, et
des sections de synthèse laissées en attente. L'étape 8 les remplit. L'étape 9
(`reels-mailler`) en dérive mécaniquement le maillage.

Tout le maillage dépend donc de ce qui est écrit ici : une fiche non enrichie
n'apparaît dans aucune note de thème ni d'entité, et reste invisible à la
navigation.

---

## 1. Ce qu'il y a à remplir

Deux endroits, et ils ne servent pas la même chose.

**Le frontmatter** — c'est la partie **machine**. `reels-mailler` ne lit que ça,
jamais la prose.

```yaml
themes: ["politique", "budget de l'État"]
entites: ["Assemblée nationale", "PLF 2026"]
```

**Le corps** — c'est la partie **humaine**, ce que tu liras dans six mois.

| Section | Contenu attendu |
|---|---|
| `> [!abstract] En une phrase` | Le propos du reel, une phrase, au style indirect |
| `## Ce que dit le reel` | Reformulation fidèle, avec les repères `[MM:SS]` sur les passages clés |
| `## Affirmations vérifiables` | Une puce par fait ou chiffre avancé, avec son horodatage |
| `## Entités citées` | Tableau `Type \| Nom` — personnes, institutions, textes, lieux |

Les sections `## Légende du post` et `## Transcript` sont déjà remplies et **ne
se touchent pas**.

---

## 2. Règles de rédaction

**Style indirect obligatoire.** « Le reel affirme que… », « l'auteur avance
que… ». Jamais « il est établi que ». Le corpus visé étant du contenu politique,
une synthèse d'apparence neutre qui reprend une affirmation militante est un
défaut, pas un détail : elle transforme un propos partisan en fait, avec
l'autorité d'une fiche.

**Aucune information qui ne vient pas de la fiche.** Ni du transcript, ni de la
légende, ni des métadonnées. Pas de complément de culture générale, pas de
contexte ajouté, pas de correction implicite. Si un chiffre paraît faux, il est
consigné tel qu'il a été dit — c'est le rôle de la section « Affirmations
vérifiables » de le rendre vérifiable, pas de trancher.

**Signaler la pauvreté plutôt que la combler.** Une fiche dont le transcript ne
porte rien d'exploitable garde ses sections en `*(rien d'exploitable)*`. Une
synthèse inventée sur un transcript vide est pire qu'une fiche vide : elle est
indétectable.

**Les horodatages renvoient à la vidéo locale.** Instagram, TikTok et Facebook
n'honorent pas de paramètre `?t=`. Écrire `[00:22]` en texte, jamais en lien vers
le post.

---

## 3. Règles de nommage des thèmes et des entités

C'est ici que se joue la qualité du maillage. Deux libellés différents pour la
même chose produisent deux notes distinctes, et la navigation se fragmente.

**Thèmes : émergents, jamais prédéfinis.** Aucune liste imposée — ils se
déduisent de ce qui est lu. Une liste décidée d'avance ferait entrer le corpus
dans des cases choisies avant de l'avoir regardé ; en les laissant émerger, on
découvre ce qui est réellement sauvegardé. De 1 à 3 par fiche, en minuscules.

**Entités : le nom propre, sous sa forme complète et usuelle.**

| Écrire | Pas |
|---|---|
| `Assemblée nationale` | `AN`, `assemblée`, `l'Assemblée nationale` |
| `PLF 2026` | `le projet de loi de finances`, `plf2026` |

Pas d'article, pas d'acronyme quand le nom complet existe, pas de qualificatif.
Types retenus : personnes, institutions, textes de loi, entreprises, lieux.

**La cohérence entre lots est le vrai risque.** Rien dans le code ne l'impose :
elle repose entièrement sur ce qui est sous les yeux au moment de rédiger. D'où
la procédure ci-dessous.

---

## 4. Procédure

**Lister ce qui reste à faire.** La commande sort les chemins bruts, un par
ligne :

```bash
uv run reels-verifier --vault ~/Vault --a-enrichir
```

**Relire les libellés déjà en place avant chaque lot.** C'est l'étape qu'on
saute et qui coûte le plus cher :

```bash
ls ~/Vault/themes ~/Vault/entites
```

**Traiter par lots de 20 à 25 fiches.** Assez pour que les libellés restent
présents à l'esprit d'un bout à l'autre, assez peu pour que la relecture reste
possible.

**Régénérer le maillage après chaque lot.** L'opération est idempotente et
instantanée :

```bash
uv run reels-mailler --vault ~/Vault
```

**Vérifier la dérive.** Après quelques lots, ouvrir `~/Vault/themes` et
`~/Vault/entites` : deux notes proches (`Assemblée nationale` et `assemblée
nationale`, `budget` et `budget de l'État`) signalent une divergence. Corriger
dans les fiches, pas dans les notes générées — elles sont réécrites à chaque
passage.

---

## 5. Contrôles avant de considérer un lot fini

- [ ] Le frontmatter est valide : `reels-mailler` lit les thèmes et entités sans les ignorer.
- [ ] Aucun libellé nouveau qui doublonne un libellé existant à la casse ou à l'article près.
- [ ] Toutes les affirmations chiffrées portent un horodatage.
- [ ] Aucune information absente du transcript, de la légende ou des métadonnées.
- [ ] Les fiches trop pauvres sont signalées comme telles, pas comblées.
- [ ] `uv run reels-verifier --vault ~/Vault` ne signale plus ces fiches.

---

## 6. Limite assumée

Cette étape est **non déterministe**. Deux passages sur la même fiche ne donnent
pas le même texte au mot près, et la cohérence des libellés dépend de ce qui a
été relu avant. C'est le prix d'une taxonomie émergente ; une liste fermée serait
reproductible mais choisirait les cases avant d'avoir vu le corpus.

Le garde-fou n'est donc pas dans le code, il est dans la procédure : relire les
libellés existants avant chaque lot, et inspecter les dossiers `themes/` et
`entites/` après.
