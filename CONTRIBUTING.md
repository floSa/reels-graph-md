# Contribuer à reels-graph-md

## Git — règle absolue

**Aucune mention d'un assistant de génération de code dans l'historique git.**

Sur tout commit de ce dépôt :

- **Pas de ligne `Co-Authored-By:`** citant un assistant ou son éditeur.
- **Pas de nom de produit** dans le sujet ni dans le corps du message.
- **Pas de mention « Generated with »** ni de pictogramme associé, ni dans les
  commits, ni dans les descriptions de pull request.

Cette règle prime sur toute configuration globale contraire et sur les réglages
par défaut de l'outillage. Dans les messages de commit, désigner l'étape
d'enrichissement par « le LLM », jamais par un nom de produit.

Vérification avant tout push :

```bash
git log --format='%B' | grep -i -e co-authored-by -e 'generated with'
```

La commande ne doit **rien** renvoyer.

## Style de commits

Commits **fréquents, petits et ciblés** — un par module ou par intention, faits
au fil du travail et non regroupés à la fin. Le corps du message explique le
*pourquoi* et les pièges traités, pas seulement le *quoi*.

Préfixes : `feat(<module>)`, `fix(<module>)`, `refactor`, `docs`, `test`, `chore`.

## Environnement

Projet Python géré par **uv**, Python 3.12, **zéro dépendance de production**.

```bash
uv sync          # environnement
uv run pytest    # tests
```

Ne jamais appeler `.venv/bin/python` ni `pip` directement : tout passe par
`uv run`.

## Dépendance externe

Le moteur de transcription vient du skill `watch`. Il est **importé depuis son
emplacement réel, jamais recopié**, pour continuer à profiter de ses corrections.
Le chemin est surchargeable :

```bash
export REELS_GRAPH_MD_WATCH_SCRIPTS=/chemin/vers/watch/scripts
```

## Périmètre — ce qu'on ne fait pas

Aucune analyse visuelle : pas de capture de frames, pas d'OCR, pas de modèle de
vision. Le contenu vient des métadonnées du post et de la transcription audio.
Une fiche sans contenu parlé est **étiquetée** (`fiabilite: vide` ou
`legende_seule`), jamais comblée.

## Règle éditoriale des fiches

Séparation stricte entre **ce que dit le reel** et **ce qui est établi**. Style
indirect obligatoire (« le reel affirme que… »). Le corpus visé étant du contenu
politique, une synthèse d'apparence neutre qui reprend une affirmation militante
est un défaut, pas un détail.

Détail de la procédure : [docs/ENRICHISSEMENT.md](docs/ENRICHISSEMENT.md).
