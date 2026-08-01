# Guide d'installation et d'utilisation

De rien du tout à un vault Obsidian consultable. À suivre dans l'ordre.

Le [README](../README.md) est une **référence** : il dit ce que fait chaque
option. Ce document est une **procédure** : il dit quoi faire, dans quel ordre,
et comment savoir que ça a marché.

**Compter deux temps très différents.** L'installation et le premier lot :
une à deux heures. L'obtention des exports de plateformes : **plusieurs jours
d'attente**, sans rien à faire. Lancer les demandes d'export en premier, puis
installer pendant que ça mûrit.

---

## Étape 1 — Demander les exports (à faire en tout premier)

Aucune plateforme n'expose d'API pour les contenus sauvegardés. Le seul chemin
est l'export officiel de tes données. C'est asynchrone : tu fais la demande, tu
reçois un courriel quelques heures à quelques jours plus tard.

**Fais les trois demandes maintenant**, avant d'installer quoi que ce soit.

| Plateforme | Chemin dans l'application | Format |
|---|---|---|
| Instagram | Centre des comptes → Vos informations et autorisations → Télécharger vos informations | **JSON** |
| TikTok | Paramètres → Compte → Télécharger vos données → *Custom data* → cocher **Likes and Favorites** | **JSON** |
| Facebook | Paramètres → Vos informations Facebook → Télécharger vos informations → cocher *Éléments enregistrés et collections* | **JSON** |

Trois pièges à ce stade :

- **Choisir JSON, pas HTML.** Le HTML fonctionne aussi (tout est lu en texte
  brut) mais il est bien plus lourd.
- **TikTok : ce sont les Favoris qu'on veut**, pas les J'aime. Le signet, pas le
  cœur. Les J'aime forment un volume bien plus gros et bien moins pertinent.
- **Sortir les fichiers du dossier Téléchargements** une fois reçus, sinon un
  nettoyage automatique les emporte.

---

> **Sans attendre les exports.** Les exports ne servent qu'à produire la *liste*
> de tes enregistrements ; le pipeline, lui, ne mange que des URLs. Dès
> l'installation faite, tu peux valider toute la chaîne en collant l'URL de
> n'importe quel reel public dans `~/Vault/inbox.txt` puis en lançant
> `uv run reels-ingest --vault ~/Vault`. Voir l'étape 5 bis.

---

## Étape 2 — Installer

### 2.1 Le projet

```bash
git clone https://github.com/floSa/reels-graph-md.git
cd reels-graph-md
uv sync
```

Aucune dépendance Python n'est téléchargée : le projet n'en a pas.

### 2.2 Les binaires externes

```bash
uv tool install yt-dlp
sudo apt install ffmpeg          # fournit aussi ffprobe
```

Vérification :

```bash
yt-dlp --version && ffmpeg -version | head -1
```

### 2.3 Le moteur de transcription

Il vient du dépôt `claude-skills`, dans `watch/scripts/`, et n'est **pas
recopié** dans ce projet — il est importé depuis son emplacement réel pour
continuer à profiter de ses corrections.

S'il n'est pas dans `~/mes_projets/claude-skills/` :

```bash
export REELS_GRAPH_MD_WATCH_SCRIPTS=/chemin/vers/watch/scripts
```

### 2.4 Le serveur Whisper

C'est le seul élément qui tourne en permanence, et il est en Docker.

```bash
~/mes_projets/claude-skills/local-whisper/speaches-up.sh up
~/mes_projets/claude-skills/local-whisper/speaches-up.sh status
```

`status` doit afficher `service : disponible`. Le premier démarrage télécharge le
modèle : compter plusieurs minutes.

> **Pour l'arrêter** : `speaches-up.sh down`. Un `docker stop` ne suffit pas —
> le conteneur porte `restart: unless-stopped` et revient au démarrage suivant de
> Docker. Voir [ARCHITECTURE.md §5](ARCHITECTURE.md#5-cycle-de-vie-des-processus).

### 2.5 Le navigateur, pour les cookies

Instagram et Facebook exigent une session authentifiée. Se connecter aux deux
dans **Firefox**, et c'est tout.

**Firefox plutôt que Chrome** : Chrome 127 et suivants chiffrent leurs cookies
avec l'API de Windows, que yt-dlp ne sait pas déchiffrer — et encore moins depuis
WSL. Firefox ne les chiffre pas.

**Il n'est pas nécessaire de fermer le navigateur.** Cette précaution vaut pour
une exécution Windows native, où Firefox verrouille sa base. Depuis WSL, la base
est copiée avant lecture : vérifié navigateur ouvert, avec trois processus
`firefox.exe` actifs.

**Cas WSL, traité automatiquement.** `--cookies-from-browser firefox` ne cherche
que dans les emplacements Linux (`~/.mozilla/firefox`…). Quand Firefox tourne
côté Windows, yt-dlp échoue avec « could not find firefox cookies database ». Le
projet détecte le cas et va chercher le profil Windows tout seul :

```
[cookies] Firefox absent de WSL — profil Windows retenu :
          /mnt/c/Users/<toi>/AppData/Roaming/Mozilla/Firefox/Profiles/xxxx.default-release
```

Pour forcer un profil précis, `--cookies` accepte aussi un chemin de dossier de
profil, ou la forme explicite `firefox:/chemin/vers/le/profil`, ou encore un
fichier `cookies.txt`.

---

## Étape 3 — Ranger les exports

Les exports arrivent en `.zip`. Décompresser, puis rassembler les fichiers utiles
au même endroit. Le nom des fichiers n'a aucune importance.

```bash
mkdir -p ~/reels-exports
# y déposer les fichiers issus des trois archives
ls ~/reels-exports
# saved_posts.json  user_data_tiktok.json  your_saved_items.json
```

> Le dossier `exports/` du dépôt est ignoré par git : si tu préfères les ranger
> là, ils ne partiront jamais dans un commit. Ils contiennent des données
> personnelles.

**Tu ne sais pas quel fichier contient quoi ?** Ce n'est pas grave. Les fichiers
sont lus en texte brut et attaqués à la regex : tu peux tous les passer, ceux qui
ne contiennent aucun lien de contenu sont simplement sans effet.

---

## Étape 4 — Vérifier avant de télécharger

**Ne jamais lancer un stock complet sans cette étape.**

```bash
uv run reels-ingest ~/reels-exports/* --vault ~/Vault --lister
```

Cette commande ne touche pas au réseau. Elle affiche ce qui serait traité :

```
[21:14:48] 3 liens de contenu trouvés, 3 à traiter.
insta_DXabc123                    https://instagram.com/reel/DXabc123
tiktok_7412345678901234567        https://tiktok.com/@un.compte/video/7412345678901234567
fb_998877665544                   https://facebook.com/reel/998877665544
```

Ce qu'il faut regarder :

| Symptôme | Cause probable |
|---|---|
| Zéro lien trouvé | Mauvais fichiers, ou export en cours de génération |
| Beaucoup moins que prévu | Une plateforme manque à l'appel — vérifier son export |
| Des liens qui ne sont pas des posts | À signaler : le filtre de contenu a un trou |

Le filtre écarte volontairement les profils, groupes, pages de réglages et
Marketplace. Un export Facebook en contient des centaines.

---

## Étape 5 — Le premier lot, sur dix reels

```bash
uv run reels-ingest ~/reels-exports/* --vault ~/Vault --cookies firefox --limite 10
```

Compter **20 à 40 secondes par reel**. La sortie ressemble à :

```
[21:20:03] [1/10] https://instagram.com/reel/DXabc123
[21:20:31]     ok — insta_DXabc123.md (fiabilité : haute)
```

### Lire le champ « fiabilité »

C'est le contrôle qualité du projet. Il dit honnêtement ce que vaut la fiche.

| Valeur | Signification | Que faire |
|---|---|---|
| `haute` | Transcript substantiel | Rien, c'est le cas nominal |
| `moyenne` | Transcript très court | Acceptable, à surveiller |
| `legende_seule` | Aucun audio exploitable, mais une légende | Normal sur un carrousel photo |
| `vide` | Ni audio ni légende | La fiche n'apportera rien |

**C'est ici que se joue la décision de continuer.** Le rapport final récapitule :

```
Fiabilité des fiches : 7 haute, 2 moyenne, 1 legende_seule
```

Si la majorité sort en `vide`, le corpus n'est pas fait de contenu parlé et le
projet ne lui apportera pas grand-chose. Mieux vaut le savoir sur 10 reels que
sur 300.

### Ouvrir le vault dans Obsidian

Ouvrir `~/Vault` comme coffre. Une fiche doit montrer un lecteur vidéo en tête,
puis la légende et le transcript horodaté. Si le lecteur ne s'affiche pas,
vérifier que le fichier existe dans `~/Vault/reels/`.

### Étape 5 bis — Tester sans attendre les exports

Pour valider la chaîne tout de suite, il suffit d'une URL publique :

```bash
echo "https://www.tiktok.com/@lemondefr/video/7669096613092003104" >> ~/Vault/inbox.txt
uv run reels-ingest --vault ~/Vault
```

TikTok ne demande pas de cookies : c'est la branche la plus simple à éprouver.
Instagram et Facebook en exigent — sans avoir à fermer Firefox.

Repères mesurés sur des reels réels : **20 secondes par reel**, **environ 3 Mo**
de vidéo, transcript fidèle sur deux minutes de parole.

---

## Étape 6 — Le stock complet

Une fois le lot de 10 concluant :

```bash
uv run reels-ingest ~/reels-exports/* --vault ~/Vault --cookies firefox --limite 50
```

**Par lots de 50, étalés sur plusieurs jours.** Instagram rate-limite sévèrement.
Pousser plus vite fait échouer des reels qui auraient marché.

Quelques repères :

- **On peut interrompre à tout moment** par `Ctrl+C`. Le journal est écrit après
  chaque reel ; relancer la même commande reprend exactement où on en était.
- **Les échecs sont retentés automatiquement** au lancement suivant. Rien à
  faire de particulier.
- **Environ un tiers d'un stock ancien est irrécupérable** : posts supprimés ou
  passés en privé. C'est normal, il n'y a pas de recours.
- **Les doublons ne coûtent rien.** Un même reel enregistré sous deux liens
  différents est détecté après l'appel aux métadonnées, avant tout
  téléchargement.

### Combien d'espace

Compter **1 à 3 Go pour 300 reels**. Les vidéos sont conservées volontairement :
c'est ce qui permet de revoir un reel dont le post d'origine a disparu.

---

## Étape 7 — Le flux continu

Une fois le stock traité, les reels sauvegardés au fil de l'eau arrivent par une
boîte de réception.

### Le raccourci mobile

Créer un raccourci de partage qui **ajoute l'URL partagée à la fin d'un fichier
texte**, synchronisé vers `~/Vault/inbox.txt`.

- **iOS** : Raccourcis → action *Ajouter au fichier texte*, restreint au type
  URL, affiché dans la feuille de partage. Passer par **iCloud Drive** : OneDrive
  se monte en lecture seule sur iOS, le raccourci ne peut pas y écrire.
- Sur iCloud, faire clic droit → **Toujours conserver sur cet appareil** sur le
  dossier. Sans cela le fichier n'est pas matérialisé localement et le script ne
  voit rien.

### Le traitement

```bash
uv run reels-ingest --vault ~/Vault --cookies firefox
```

Sans argument positionnel : seule l'inbox est lue. Les lignes traitées partent
dans `inbox-traite.txt`, celles qui ont échoué restent en place pour la fois
suivante. Une URL ajoutée par le raccourci **pendant** que le traitement tourne
n'est pas perdue.

---

## Étape 8 — Enrichir les fiches

Les fiches sortent brutes : `themes: []`, `entites: []`, sections de synthèse en
attente. Tant qu'elles ne sont pas remplies, **aucune navigation n'est possible**.

```bash
uv run reels-verifier --vault ~/Vault --a-enrichir
```

La procédure complète, les règles de rédaction et les règles de nommage sont dans
[ENRICHISSEMENT.md](ENRICHISSEMENT.md). C'est la seule étape non automatisée.

---

## Étape 9 — Générer le maillage

```bash
uv run reels-mailler --vault ~/Vault
```

Instantané, sans IA, idempotent — à relancer après chaque lot d'enrichissement.

```
25 fiches lues.
8 thèmes, 34 entités.
25 fiches mises à jour.
```

Le vault contient alors :

```text
Vault/
├── fiches/            une fiche par reel
├── reels/             les vidéos
├── themes/            politique.md, budget de l'État.md…
├── entites/           Assemblée nationale.md, PLF 2026.md…
├── journal.json
├── inbox.txt
└── inbox-traite.txt
```

Dans Obsidian : ouvrir `themes/politique.md` pour voir tous les reels du thème,
`entites/Assemblée nationale.md` pour tous ceux qui la mentionnent. `Ctrl+G`
affiche la vue graphe.

---

## Étape 10 — Entretenir

```bash
uv run reels-verifier --vault ~/Vault
```

À passer de temps en temps, et systématiquement après avoir déplacé ou supprimé
des fichiers à la main. La commande confronte le journal au disque.

```bash
uv run reels-verifier --vault ~/Vault --reparer
```

Remet en file les entrées que le disque contredit — une vidéo supprimée pour
gagner de la place, une fiche effacée par erreur. Rien n'est détruit : le reel
sera simplement refait au prochain `reels-ingest`.

---

## Questions fréquentes

**Comment savoir qu'une vidéo a déjà été traitée ?**
`journal.json` est la référence, indexé par URL canonique. Deux garde-fous se
cumulent : les variantes d'une même URL (`?igshid=`, slash final, `www.`)
convergent avant tout appel réseau ; et après l'appel aux métadonnées, un
contrôle sur l'identifiant que la plateforme renvoie elle-même rattrape les cas
que l'URL ne peut pas trancher, comme un lien court `vm.tiktok.com` face à sa
forme résolue. Dans les deux cas, rien n'est téléchargé deux fois.

**Y a-t-il une file d'attente ?**
Non, pas au sens d'une file persistante. La liste de travail est **recalculée à
chaque lancement** : tous les liens des sources, moins ce que le journal donne
pour fait. **Conséquence à connaître : les fichiers d'export doivent rester
disponibles.** Si tu les supprimes, le journal seul ne sait pas reconstruire la
liste — il enregistre ce qui est fait, pas ce qui reste.

**Comment arrêter le pipeline ?**
`Ctrl+C`. C'est un moyen d'arrêt légitime, pas un incident. Les commandes sont
des traitements par lots : elles démarrent, travaillent et rendent la main. Rien
ne reste allumé côté projet.

**Qu'est-ce qui tourne en permanence, alors ?**
Le seul service est le serveur Whisper, en Docker, **hors de ce dépôt**. Arrêt
définitif par `speaches-up.sh down`.

**Puis-je déplacer le vault ?**
Oui. Les liens vers les vidéos sont relatifs. Déplacer le dossier entier ne casse
rien.

**Puis-je supprimer les vidéos pour gagner de la place ?**
Oui, mais tu perds la possibilité de revoir le reel — le lien d'origine est mort
dans environ un tiers des cas. Après suppression, passer `reels-verifier` :
sinon le journal continue d'affirmer que tout est en place.

**Une fiche est fausse ou mal enrichie, que faire ?**
Corriger la fiche à la main, puis relancer `reels-mailler`. Ne jamais corriger
dans `themes/` ou `entites/` : ces dossiers sont réécrits à chaque passage.

---

## Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `Failed to decrypt with DPAPI` | Chrome 127+ chiffre ses cookies | Utiliser Firefox. Pas de contournement |
| `could not find firefox cookies database` | Profil cherché côté Linux alors que Firefox tourne sous Windows | Détecté automatiquement sous WSL ; sinon passer le chemin du profil à `--cookies` |
| Sortie en code `3` | Serveur Whisper injoignable | `speaches-up.sh up`, puis relancer |
| Sortie en code `2` | Aucune source, ou fichier introuvable | Vérifier les chemins passés |
| Transcript dans la mauvaise langue | Corpus non francophone | `--langue en` |
| Beaucoup de `fiabilite: vide` | Reels sans voix off | Limite du périmètre, pas un bug |
| Échecs en rafale sur Instagram | Rate-limit | Attendre, réduire les lots, augmenter `--pause` |
| Le lecteur vidéo ne s'affiche pas | Vidéo absente | `reels-verifier --reparer` puis relancer l'ingestion |
| Deux notes proches dans `themes/` | Libellés divergents entre lots | Corriger dans les fiches, relancer `reels-mailler` |
