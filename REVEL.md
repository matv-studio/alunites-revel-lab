# Dépôt cobaye de Revel

Copie du site alunites.com servant à tester l'application Revel (dépôt `matv-studio/Revel`).

| Fichier | Rôle |
|---|---|
| `site.revel.json` | Site au format Revel, produit par `revel import-eleventy .` (pages, gabarits, composants, collections) |
| `revel-import.json` | Profil d'import : traduction en expressions de la logique JavaScript d'Eleventy (filtres, plan du site, environnements) |
| `src/assets/fonts/` | Polices Montserrat (licence OFL, `OFL-montserrat.txt`), recopiées depuis `node_modules` pour que Revel n'en dépende pas |

Les contenus (`src/content`), données (`src/_data`) et médias (`src/media`) ne changent pas : Pages CMS et
Eleventy continuent de fonctionner pendant la transition.

Génération avec Revel : `revel build . --out _site` (environnement `production` par défaut, `--env staging` pour la recette).
