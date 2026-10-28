# Site Alunites (Revel)

Site de l'agence [Alunites](https://alunites.com), au format de [Revel](https://github.com/matv-studio/Revel) :
à ouvrir dans Revel (« Ouvrir un site » sur ce dossier), où tout se modifie depuis l'interface.

| Fichier ou dossier | Rôle |
|---|---|
| `site.revel.json` | Le site : 8 pages, 4 gabarits, 13 composants, couleurs claires et sombres, styles |
| `content/` | Contenus du CMS : projets, actualités, expertises, équipe, rubriques |
| `.pages.yml` | Champs des collections (compatible Pages CMS) |
| `media/` | Images, vidéos, polices |

Générer le site sans l'interface : `revel build . --out _site`.

Cette version, recréée dans Revel (direction « Rayonner », 27/10/2026), remplace le site Eleventy d'origine.
Le site Eleventy reste dans l'historique du dépôt (commit `0dd004c`), utilisé par les essais de Revel.
