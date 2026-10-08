<?php
/**
 * Formulaire de contact alunites.com — traitement côté serveur (hébergement OVH, PHP).
 *
 * Reçoit le POST du formulaire /contact/ (fetch) et envoie un e-mail au destinataire.
 * Protections : champ piège (honeypot), délai minimal de saisie, limite de longueur,
 * filtrage des en-têtes, limite de fréquence par IP (fichier temporaire).
 *
 * Compatible PHP 7.0 et versions suivantes (l'hébergement OVH tourne actuellement en PHP 7.0).
 *
 * L'adresse d'envoi (From) doit appartenir au domaine alunites.com. Pour une bonne
 * délivrabilité, l'enregistrement SPF du domaine doit autoriser les serveurs d'envoi
 * OVH (voir README, section « Formulaire de contact »).
 */

declare(strict_types=1);

const RECIPIENT = 'contact@alunites.com';
const FROM      = 'site@alunites.com';
const SUBJECT   = 'Nouveau message depuis alunites.com';
const MIN_SECONDS = 3;      // un humain met plus de 3 s à remplir le formulaire
const MAX_PER_HOUR = 5;     // envois maximum par IP et par heure

date_default_timezone_set('Europe/Paris');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply(int $code, bool $ok, string $message = '') {
    http_response_code($code);
    echo json_encode(['ok' => $ok, 'message' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    reply(405, false, 'Méthode non autorisée.');
}

// Même origine uniquement
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin !== '' && !preg_match('#^https://([a-z0-9-]+\.)?alunites\.com$#', $origin)) {
    reply(403, false, 'Origine refusée.');
}

$field = static function (string $k, int $max): string {
    return mb_substr(trim((string)($_POST[$k] ?? '')), 0, $max);
};

$name    = $field('name', 120);
$email   = $field('email', 200);
$message = $field('message', 5000);
$trap    = $field('website', 200);
$ts      = (int)($_POST['ts'] ?? 0);

// Robots : on répond « ok » sans envoyer
if ($trap !== '' || ($ts > 0 && (time() - intdiv($ts, 1000)) < MIN_SECONDS)) {
    reply(200, true);
}

if ($name === '' || $message === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    reply(422, false, 'Merci de renseigner votre nom, une adresse e-mail valide et votre message.');
}

// Limite de fréquence par IP
$ip = $_SERVER['REMOTE_ADDR'] ?? 'inconnue';
$bucket = sys_get_temp_dir() . '/alunites-contact-' . hash('sha256', $ip);
$now = time();
$hits = [];
if (is_file($bucket)) {
    $hits = array_filter(array_map('intval', explode(',', (string)file_get_contents($bucket))), static function ($t) use ($now) {
        return $t > $now - 3600;
    });
}
if (count($hits) >= MAX_PER_HOUR) {
    reply(429, false, 'Trop de messages envoyés depuis votre connexion. Réessayez dans une heure ou écrivez à ' . RECIPIENT . '.');
}
$hits[] = $now;
@file_put_contents($bucket, implode(',', $hits), LOCK_EX);

// Aucun retour à la ligne dans les valeurs d'en-tête
$clean = static function (string $v): string {
    return str_replace(["\r", "\n", '%0a', '%0d'], ' ', $v);
};

$body  = "Nouveau message reçu depuis le formulaire de contact d'alunites.com\n\n";
$body .= "Nom : {$name}\n";
$body .= "E-mail : {$email}\n";
$body .= 'Date : ' . date('d/m/Y H:i') . "\n\n";
$body .= "Message :\n{$message}\n";

$headers = [
    'From: Site Alunites <' . FROM . '>',
    'Reply-To: ' . $clean($name) . ' <' . $clean($email) . '>',
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    'X-Mailer: alunites.com',
];

$subject = '=?UTF-8?B?' . base64_encode(SUBJECT . ' — ' . $clean($name)) . '?=';
$sent = mail(RECIPIENT, $subject, $body, implode("\r\n", $headers), '-f' . FROM);

if (!$sent) {
    reply(500, false, "Le message n'a pas pu être envoyé. Écrivez-nous directement à " . RECIPIENT . '.');
}
reply(200, true);
