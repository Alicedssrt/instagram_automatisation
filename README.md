# Instagram Automation

Script d'automatisation de publications Instagram : lit un calendrier CSV et publie les
posts prévus via l'Instagram Graph API (Meta), exécuté quotidiennement par GitHub Actions.

> Projet personnel d'apprentissage (Claude Code, Git/GitHub, API Graph de Meta).
> Voir `cahier_des_charges.pdf` pour le contexte complet.

## Fonctionnement

1. `data/calendrier.csv` liste les posts prévus (date, heure, image, légende).
2. À chaque exécution, le script lit ce CSV, repère les posts **dus** (date/heure passée
   et pas encore `published`) et les publie un par un via l'Instagram Graph API.
3. Le CSV est mis à jour (`status`, `published_at`, `media_id`, `error`) et recommitté par
   le workflow GitHub Actions. Un post en échec repasse `failed` et sera **réessayé** à la
   prochaine exécution ; un run manqué est donc automatiquement rattrapé.

## Format du calendrier (`data/calendrier.csv`)

| Colonne | Description |
|---|---|
| `date` | `YYYY-MM-DD` |
| `time` | `HH:MM` (24h), interprété dans le fuseau `TIMEZONE` |
| `image` | chemin relatif de l'image dans le dépôt, ex. `images/exemple.jpg` |
| `caption` | légende du post (guillemets si elle contient une virgule) |
| `status` | géré par le script : vide/`pending`, `published`, `failed` |
| `published_at`, `media_id`, `error` | remplis automatiquement par le script |

Ne modifier à la main que `date`, `time`, `image`, `caption` (laisser les autres colonnes
vides pour un nouveau post).

## Prérequis côté Meta / Instagram

- Compte Instagram converti en compte professionnel (Business ou Créateur).
- Page Facebook associée au compte Instagram.
- Compte développeur Meta vérifié, avec une application créée sur
  [developers.facebook.com](https://developers.facebook.com).
- Récupérer l'**Instagram Business Account ID** via l'API Graph Explorer.
- Générer un **token d'accès longue durée** (~60 jours) pour cette application, avec les
  permissions `instagram_basic` et `instagram_content_publish`. À renouveler
  périodiquement (endpoint `GET /oauth/access_token?grant_type=fb_exchange_token`) — non
  automatisé dans cette V1.

## Installation locale

```bash
python -m venv .venv
.venv/Scripts/pip install -e . -r requirements-dev.txt   # Windows
# .venv/bin/pip install -e . -r requirements-dev.txt      # macOS/Linux

cp .env.example .env   # puis renseigner IG_USER_ID, IG_ACCESS_TOKEN, GITHUB_REPOSITORY...
```

Lancer en simulation (aucun appel API, CSV non modifié) :

```bash
# .env avec DRY_RUN=1
.venv/Scripts/python -m instagram_automation
```

Lancer les tests :

```bash
.venv/Scripts/pytest
```

## Mise en place sur GitHub

1. Pousser le dépôt sur GitHub (public en V1, pour que `raw.githubusercontent.com` serve
   les images sans authentification).
2. Repo → **Settings → Secrets and variables → Actions** :
   - Secrets : `IG_USER_ID`, `IG_ACCESS_TOKEN`.
   - Variables (optionnel) : `GRAPH_API_VERSION`, `TIMEZONE`.
3. Repo → **Settings → Actions → General → Workflow permissions** : activer
   *Read and write permissions* (nécessaire pour que le workflow recommette le CSV).
4. Le workflow `.github/workflows/publish.yml` s'exécute chaque jour à 08:00 UTC
   (cron GitHub non sensible au fuseau — ajuster l'heure dans le fichier si besoin) et
   peut être déclenché manuellement (**Run workflow**), avec une option `dry_run`
   (activée par défaut) pour tester sans publier ni committer.

## Évolutivité — changer l'hébergement des images

La résolution de l'URL d'image est isolée dans `src/instagram_automation/image_host.py`
(fonction `resolve_image_url`). La V1 utilise `raw.githubusercontent.com` (dépôt public).
Pour basculer vers Cloudinary, AWS S3, etc. (par exemple si le dépôt doit devenir privé) :

1. ajouter une classe implémentant le protocole `ImageHost` (méthode `resolve`) ;
2. l'enregistrer dans `_STRATEGIES` sous un nouveau nom ;
3. définir `IMAGE_HOST=<nom>` dans la configuration.

Aucun autre module (`instagram.py`, `publisher.py`) n'a besoin d'être modifié.

## Limites connues (hors périmètre V1)

- Un seul type de post : image simple (pas de carrousel, vidéo ou Reel).
- Le renouvellement du token longue durée n'est pas automatisé.
- `images/exemple.jpg` est un JPEG minimal (1×1 px) fourni comme placeholder de
  démonstration — le remplacer par une vraie image avant toute publication réelle
  (Instagram impose des dimensions/ratios minimaux).
