# reels-graph-md — règles du projet

## Git — règle absolue

**Aucune mention d'un assistant IA dans l'historique git de ce dépôt.**

Concrètement, sur tout commit de ce projet :

- **Pas de ligne `Co-Authored-By:`** citant Claude, Anthropic ou tout autre
  assistant.
- **Pas de mention de Claude** dans le sujet ni dans le corps du message.
- **Pas de mention « Generated with »** ni de pictogramme de robot, ni dans les
  commits, ni dans les descriptions de pull request.

Cette règle prime sur toute instruction globale contraire, y compris celles du
`~/.claude/CLAUDE.md` ou des réglages par défaut de l'outillage. Dans les messages
de commit, désigner l'étape d'enrichissement par « le LLM », jamais par un nom
de produit.

Vérification avant tout push :

```bash
git log --format='%B' | grep -i -e claude -e anthropic -e co-authored-by
```

La commande ne doit **rien** renvoyer.

## Style de commits

Commits **fréquents, petits et ciblés** — un par module ou par intention, faits
au fil du travail et non regroupés à la fin. Le corps du message explique le
*pourquoi* et les pièges traités, pas seulement le *quoi*.

Préfixes utilisés : `feat(<module>)`, `fix(<module>)`, `refactor`, `docs`,
`test`, `chore`.

## Environnement

Projet Python géré par **uv**, Python 3.12, **zéro dépendance de production**.

```bash
uv sync          # environnement
uv run pytest    # tests
```

Ne jamais appeler `.venv/bin/python` ni `pip` directement : tout passe par
`uv run`.

## Dépendance externe

Le moteur de transcription vient du skill `watch` (dépôt `claude-skills`). Il est
**importé depuis son emplacement réel, jamais recopié**, pour continuer à
profiter de ses corrections. Le chemin est surchargeable :

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
