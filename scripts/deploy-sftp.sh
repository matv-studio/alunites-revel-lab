#!/usr/bin/env bash
# Publie le dossier _site/ sur l'hébergement OVH par SFTP (port 22, transfert chiffré).
#
# N'envoie que les fichiers modifiés depuis la dernière mise en ligne : l'empreinte (SHA-1)
# de chaque fichier publié est conservée dans un manifeste stocké sur l'hébergement, hors des
# dossiers publics (~/.deploy/<dossier>.manifest). Les fichiers disparus du site sont supprimés
# du serveur ; les fichiers que le site n'a jamais publiés ne sont pas touchés.
#
# Variables d'environnement :
#   SFTP_HOST         serveur (« Serveur FTP et SFTP » dans l'onglet FTP - SSH d'OVH)
#   SFTP_USER         identifiant FTP
#   LFTP_PASSWORD     mot de passe FTP (lu par lftp, jamais affiché)
#   SFTP_PORT         port (défaut 22)
#   REMOTE_DIR        dossier racine du site sur l'hébergement, relatif au dossier personnel (défaut www/)
#   LOCAL_DIR         dossier à publier (défaut _site)
#   SFTP_KNOWN_HOSTS  facultatif : clé publique du serveur au format known_hosts, pour la vérifier
#   FULL_SYNC         « 1 » pour renvoyer tous les fichiers (ignore le manifeste)
#   DRY_RUN           « 1 » pour afficher ce qui serait envoyé / supprimé sans rien modifier
set -euo pipefail
export LC_ALL=C

: "${SFTP_HOST:?SFTP_HOST manquant (secret OVH_FTP_SERVER)}"
: "${SFTP_USER:?SFTP_USER manquant (secret OVH_FTP_USERNAME)}"
: "${LFTP_PASSWORD:?LFTP_PASSWORD manquant (secret OVH_FTP_PASSWORD)}"
PORT="${SFTP_PORT:-22}"
LOCAL_DIR="${LOCAL_DIR:-_site}"
REMOTE_DIR="${REMOTE_DIR:-www/}"
REMOTE_DIR="${REMOTE_DIR#./}"
REMOTE_DIR="${REMOTE_DIR%/}"
[ -n "$REMOTE_DIR" ] && [ "$REMOTE_DIR" != "." ] && [ "${REMOTE_DIR#/}" = "$REMOTE_DIR" ] \
  || { echo "REMOTE_DIR doit être un dossier relatif non vide (ex. www/ ou recette-v4k8/)" >&2; exit 1; }
[ -d "$LOCAL_DIR" ] || { echo "Dossier local introuvable : $LOCAL_DIR" >&2; exit 1; }
MANIFEST=".deploy/$(printf '%s' "$REMOTE_DIR" | tr '/' '_').manifest"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --- Clé du serveur -------------------------------------------------------------------------
KNOWN="$WORK/known_hosts"
if [ -n "${SFTP_KNOWN_HOSTS:-}" ]; then
  printf '%s\n' "$SFTP_KNOWN_HOSTS" > "$KNOWN"
  CHECK=yes
else
  : > "$KNOWN"
  CHECK=accept-new
fi

lftp_run() {
  # $1 : commandes lftp exécutées après la connexion
  lftp -c "
set cmd:fail-exit yes
set xfer:clobber yes
set xfer:use-temp-file ${ATOMIC:-no}
set net:timeout 30
set net:max-retries 3
set net:reconnect-interval-base 5
set sftp:auto-confirm no
set sftp:connect-program 'ssh -a -x -o StrictHostKeyChecking=$CHECK -o UserKnownHostsFile=$KNOWN -o HashKnownHosts=no -o PreferredAuthentications=password,keyboard-interactive -o PubkeyAuthentication=no -o ServerAliveInterval=20'
open --env-password -u '$SFTP_USER' 'sftp://$SFTP_HOST:$PORT'
$1"
}

# --- 1. Connexion + dossier distant + manifeste précédent -----------------------------------
echo "Connexion à $SFTP_HOST:$PORT (dossier $REMOTE_DIR/)…"
lftp_run "
mkdir -p -f '$REMOTE_DIR'
mkdir -p -f .deploy
cd '$REMOTE_DIR'"
if [ "$CHECK" = accept-new ]; then
  echo "::warning::Clé du serveur non vérifiée (variable OVH_SSH_KNOWN_HOSTS absente). Clé reçue, à copier dans OVH_SSH_KNOWN_HOSTS pour la figer :"
  cat "$KNOWN"
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
      echo "### Clé du serveur SFTP"
      echo "À copier telle quelle dans la variable \`OVH_SSH_KNOWN_HOSTS\` (Settings > Secrets and variables > Actions > Variables) :"
      echo '```'
      cat "$KNOWN"
      echo '```'
    } >> "$GITHUB_STEP_SUMMARY"
  fi
  CHECK=yes   # les connexions suivantes de ce déploiement doivent présenter la même clé
fi

# Remplacement atomique : chaque fichier est envoyé sous un nom temporaire puis renommé, pour
# qu'un visiteur ne tombe jamais sur un fichier absent ou à moitié écrit. Testé au préalable,
# car tous les serveurs SFTP n'acceptent pas de renommer par-dessus un fichier existant.
printf 'ok\n' > "$WORK/probe"
if ATOMIC=yes lftp_run "put '$WORK/probe' -o .deploy/probe; put '$WORK/probe' -o .deploy/probe; rm -f .deploy/probe" >/dev/null 2>&1; then
  ATOMIC=yes
else
  ATOMIC=no
  lftp_run "set cmd:fail-exit no; rm -f .deploy/probe .deploy/.in.probe" >/dev/null 2>&1 || true
  echo "Remplacement atomique non pris en charge par le serveur : envoi direct des fichiers."
fi

if [ "${FULL_SYNC:-}" = "1" ] || ! lftp_run "get '$MANIFEST' -o '$WORK/old'" >/dev/null 2>&1; then
  : > "$WORK/old"   # premier envoi (ou envoi complet demandé) : tout est envoyé
fi

# --- 2. Manifeste du site construit -----------------------------------------------------------
(
  cd "$LOCAL_DIR"
  find . -type f -printf '%P\n' | sort > "$WORK/files"
  if grep -q -E '[\\"]' "$WORK/files"; then
    echo "Nom de fichier non pris en charge (guillemet ou antislash) :" >&2
    grep -E '[\\"]' "$WORK/files" >&2
    exit 1
  fi
  tr '\n' '\0' < "$WORK/files" | xargs -0 -r sha1sum
) | sort -k2 > "$WORK/new"

# Fichiers nouveaux ou modifiés (empreinte + chemin absents de l'ancien manifeste)
comm -13 <(sort "$WORK/old") <(sort "$WORK/new") | cut -c43- | sort > "$WORK/upload"
# Fichiers publiés la dernière fois et absents du nouveau site
comm -23 <(cut -c43- "$WORK/old" | sort) <(cut -c43- "$WORK/new" | sort) > "$WORK/delete"

n_up=$(wc -l < "$WORK/upload"); n_del=$(wc -l < "$WORK/delete"); n_all=$(wc -l < "$WORK/new")
size_up=$(cd "$LOCAL_DIR" && tr '\n' '\0' < "$WORK/upload" | xargs -0 -r stat -c %s | awk '{s+=$1} END {print s+0}')
echo "Site : $n_all fichiers. À envoyer : $n_up ($(( ${size_up:-0} / 1048576 )) Mo). À supprimer : $n_del."

if [ "${DRY_RUN:-}" = "1" ]; then
  echo "--- Envoi (aperçu) ---"; head -50 "$WORK/upload"
  echo "--- Suppression (aperçu) ---"; head -50 "$WORK/delete"
  exit 0
fi

# Avant toute modification, le manifeste distant perd les fichiers à renvoyer : si l'envoi est
# interrompu, ils seront renvoyés la fois suivante (et les suppressions seront refaites).
if [ "$n_up" -gt 0 ] || [ "$n_del" -gt 0 ]; then
  awk -v list="$WORK/upload" 'BEGIN { while ((getline l < list) > 0) up[l] = 1 }
                              !(substr($0, 43) in up)' "$WORK/old" > "$WORK/stable"
  lftp_run "put '$WORK/stable' -o '$MANIFEST'"
fi

# --- 3. Envoi des fichiers modifiés (copie temporaire ne contenant qu'eux) --------------------
if [ "$n_up" -gt 0 ]; then
  STAGE="$WORK/stage"
  mkdir -p "$STAGE"
  (cd "$LOCAL_DIR" && tr '\n' '\0' < "$WORK/upload" | xargs -0 cp --parents -t "$STAGE")
  lftp_run "mirror --reverse --transfer-all --no-perms --no-umask --parallel=4 --verbose=1 '$STAGE' '$REMOTE_DIR'"
fi

# --- 4. Suppression des fichiers retirés du site ----------------------------------------------
if [ "$n_del" -gt 0 ]; then
  {
    echo "set cmd:fail-exit no"
    echo "cd '$REMOTE_DIR'"
    sed 's/.*/rm -f "&"/' "$WORK/delete"
  } > "$WORK/delete.lftp"
  lftp_run "source '$WORK/delete.lftp'"
fi

# --- 5. Manifeste complet, enregistré une fois tout le reste réussi --------------------------
lftp_run "put '$WORK/new' -o '$MANIFEST'"
echo "Mise en ligne terminée."
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  echo "Mise en ligne SFTP dans \`$REMOTE_DIR/\` : $n_all fichiers sur le site, $n_up envoyés, $n_del supprimés." >> "$GITHUB_STEP_SUMMARY"
fi
