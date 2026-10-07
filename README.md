# alunites.com

Site de l'agence Alunites, reconstruit à partir du site WordPress d'origine. Le site est statique, généré par [Eleventy](https://www.11ty.dev/), et ses contenus se modifient dans [Pages CMS](https://pagescms.org/). Chaque modification est publiée automatiquement sur l'hébergement OVH par GitHub Actions.

```
contenu (Pages CMS ou fichiers) ──commit──▶ GitHub ──Actions : build Eleventy──▶ FTP ──▶ OVH (www/)
```

## Arborescence

| Dossier / fichier | Rôle |
| --- | --- |
| `src/content/projets/` | 1 fichier par projet → `/project/<slug>/` (URL WordPress conservée) |
| `src/content/actualites/` | 1 fichier par actualité → `/<slug>/` (URL WordPress conservée) |
| `src/content/expertises/` | 4 expertises → `/expertise/<slug>/` |
| `src/content/equipe/`, `src/content/offres/` | Équipe et offres d'emploi (affichées sur `/agence/`) |
| `src/_data/pages/*.yml` | Textes des pages Accueil, Agence, Contact, Projets, Actualités, Mentions légales |
| `src/_data/site.yml` | Coordonnées, réseaux sociaux, identifiant Google Analytics, textes communs |
| `src/_data/clients.yml` | Logos clients |
| `src/media/` | Images, vidéos et PDF (ancien `/app/uploads/`) |
| `src/_includes/`, `src/assets/` | Gabarits, CSS, JavaScript, logos |
| `src/htaccess.njk` | Génère le `.htaccess` : HTTPS, redirections 301, cache |
| `src/static/contact.php` | Envoi du formulaire de contact (PHP sur OVH) |
| `.pages.yml` | Configuration de l'interface Pages CMS |
| `.github/workflows/deploy.yml` | Construction et mise en ligne |
| `_import/` | Outils de migration depuis WordPress (non publiés) |

## Travailler en local

Prérequis : Node.js 20 ou plus récent.

```bash
npm install
npm run dev      # http://localhost:8080, rechargement automatique
npm run build    # génère le site dans _site/
```

## Modifier le contenu (Pages CMS)

1. Aller sur https://app.pagescms.org et se connecter avec le compte GitHub qui a accès au dépôt.
2. Ouvrir le dépôt. Les rubriques Projets, Actualités, Expertises, Équipe, Offres d'emploi, Pages, Logos clients et Réglages du site apparaissent.
3. Pour donner accès à quelqu'un sans compte GitHub : Pages CMS > Settings > Collaborators, invitation par e-mail.

Chaque « Save » crée un commit sur `main`. Le site est reconstruit et mis en ligne en 2 à 5 minutes (suivi dans l'onglet Actions de GitHub).

Conventions :

- Titres de section : les mots entre astérisques sont mis en couleur, par exemple `nos dernières *réalisations*`.
- Slug : il fixe l'adresse de la page. Ne pas le modifier après publication, l'ancienne adresse ne fonctionnerait plus.
- Brouillon : décocher « Publié ». La page n'est alors pas générée.
- Vidéos : coller le lien direct Vimeo (`https://player.vimeo.com/progressive_redirect/…/file.mp4…`), un lien de page Vimeo ou un lien YouTube. Les liens directs Vimeo n'expirent pas, mais ils cessent de fonctionner si le compte Vimeo passe à une offre gratuite ou Starter.
- Images : déposer de préférence des fichiers d'au moins 2000 px de large. Les versions AVIF et WebP sont générées automatiquement.

## Médias et placeholders

Toute image référencée mais absente de `src/media/` est remplacée par un placeholder « Visuel à venir » portant le nom du fichier attendu. Le build ne bloque pas. La vérification des liens (`node scripts/check-links.mjs`) liste les médias manquants.

Récupération depuis l'ancien site : lancer `TELECHARGER-MEDIAS.cmd` sous Windows (télécharge `_import/medias-originaux/`), puis `node _import/tools/optimize-media.mjs` (redimensionne à 2560 px maximum et compresse vers `src/media/`).

## Référencement (SEO) : ce qui est conservé

- **URL** : toutes les URL de projets, d'actualités, d'expertises et de pages sont identiques à celles de WordPress.
- **Titres et descriptions** : ce sont ceux saisis dans WordPress (champs « Meta »), avec la même règle : « Titre SEO | Alunites - Agence de communication plurielle », ou le nom du site seul si le champ est vide.
- **Redirections 301** (fichier `.htaccess`) :
  - `/app/uploads/AAAA/MM/fichier` → `/media/AAAA/MM/fichier` (y compris les déclinaisons `-1024x683`) ;
  - offres `/?job=…` → PDF de l'offre ;
  - liens courts `/?p=ID` et `/?page_id=ID` → page correspondante ;
  - `/people/…` → `/agence/#equipe` ;
  - `/category/…` et `/tag/…` → `/actualites/` ;
  - `/feed/` → `/feed.xml`, `/wp-sitemap*.xml` → `/sitemap.xml` ;
  - pages de pièces jointes → page parente ;
  - `http://` et `www.` → `https://alunites.com/`.
  - Google recommande de garder ces redirections au moins un an.
- **Sitemap** `/sitemap.xml` et `robots.txt` : générés automatiquement.
- **Search Console** : la propriété est validée par un enregistrement DNS TXT (`google-site-verification=…`), indépendant de l'hébergement. Il ne faut pas supprimer cet enregistrement.
- **Google Analytics 4** : même identifiant `G-BJS928QSN3`, donc historique conservé. Le script n'est chargé qu'après consentement (bandeau cookies, conformité CNIL).
- **Données structurées** : l'organisation déclarée est désormais Alunites (WordPress déclarait « Cher Ami », le nom du prestataire).

## Mise en ligne sur OVH

1. Dans GitHub, onglet Settings > Secrets and variables > Actions :
   - Secrets : `OVH_FTP_SERVER` (ex. `ftp.cluster0XX.hosting.ovh.net`), `OVH_FTP_USERNAME`, `OVH_FTP_PASSWORD`. Ces valeurs sont dans l'espace client OVH, rubrique Web Cloud > Hébergements > onglet « FTP - SSH ».
   - Variables : `OVH_FTP_DIR` (dossier racine, `www/` par défaut), `OVH_FTP_PROTOCOL` (`ftps` par défaut, `ftp` si la connexion chiffrée échoue).
2. Premier envoi : mettre la variable `DEPLOY_ENABLED` à `true`, puis lancer l'action « Construire et publier » (onglet Actions > Run workflow).
3. Vérifier le site sur l'adresse technique OVH, ou via le fichier `hosts` de son ordinateur, avant la bascule DNS.

## Bascule DNS (le jour J)

Le domaine et sa zone DNS sont chez OVH. Le site actuel est hébergé chez Infomaniak (IP `83.166.130.137`). Les e-mails passent par Microsoft 365.

1. La veille, baisser le TTL des enregistrements `A` et `CNAME www` à 300 s.
2. Remplacer l'enregistrement `A` de `alunites.com` par l'IP de l'hébergement OVH (indiquée dans l'onglet « Informations générales » de l'hébergement). Le `CNAME www` peut rester sur `alunites.com`.
3. Ne pas toucher aux enregistrements `MX`, `TXT` (SPF, google-site-verification, MS=…, brevo-code) ni `autodiscover`.
4. Activer le certificat SSL gratuit de l'hébergement OVH (Let's Encrypt) pour `alunites.com` et `www.alunites.com`.
5. Contrôles :
   - quelques anciennes URL (projets, actualités, `/app/uploads/…`, `/?job=…`) aboutissent bien ;
   - le formulaire de contact fonctionne ;
   - dans Search Console : soumettre `https://alunites.com/sitemap.xml`, puis surveiller l'indexation et le rapport « Pages » pendant 2 à 3 semaines.
6. Garder l'hébergement Infomaniak quelques semaines, puis le résilier.

## Formulaire de contact

`contact.php` envoie les messages à `contact@alunites.com` avec la fonction PHP `mail()` de l'hébergement OVH. L'expéditeur est `site@alunites.com` et la réponse se fait directement à l'auteur du message. Protections en place : champ piège, délai minimal de saisie, limite de 5 envois par heure et par IP.

**Délivrabilité, à faire avant la bascule** : l'enregistrement SPF actuel est `v=spf1 include:spf.protection.outlook.com ip4:213.186.33.87 mx -all`. Il refuse (`-all`) tout serveur non listé, donc les messages envoyés depuis l'hébergement OVH risquent d'être rejetés. Ajouter l'include OVH :

```
v=spf1 include:spf.protection.outlook.com include:mx.ovh.com ip4:213.186.33.87 mx -all
```

Après la mise en ligne, envoyer un message de test et vérifier qu'il n'arrive pas en courrier indésirable.

## À mettre à jour avant la mise en ligne

- **Mentions légales** : la rubrique « Hébergement » cite Infomaniak. Il faudra indiquer OVH SAS (2 rue Kellermann, 59100 Roubaix, France) une fois la bascule faite (Pages CMS > Page — Mentions légales).
- **Bandeau cookies** : le texte renvoie aux mentions légales. Il peut être utile d'y ajouter un paragraphe sur Google Analytics.
