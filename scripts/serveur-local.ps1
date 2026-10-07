# Serveur web local pour tester le site genere (_site) sous Windows, sans rien installer.
# Lance par TESTER-EN-LOCAL.cmd. Adresse : http://localhost:8080/  (Ctrl+C pour arreter)
# Limites : pas de PHP (le formulaire de contact ne part pas en local) ni de .htaccess (redirections).

param([int]$Port = 8080)

$ErrorActionPreference = 'Stop'
$root = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) '_site'
if (-not (Test-Path (Join-Path $root 'index.html'))) {
    Write-Host "Le dossier _site est vide : le site n'a pas encore ete genere." -ForegroundColor Red
    exit 1
}

$types = @{
    '.html' = 'text/html; charset=utf-8'; '.css' = 'text/css; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'
    '.json' = 'application/json'; '.xml' = 'application/xml; charset=utf-8'; '.txt' = 'text/plain; charset=utf-8'
    '.svg' = 'image/svg+xml'; '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.jpeg' = 'image/jpeg'; '.gif' = 'image/gif'
    '.webp' = 'image/webp'; '.avif' = 'image/avif'; '.ico' = 'image/x-icon'; '.pdf' = 'application/pdf'
    '.woff2' = 'font/woff2'; '.woff' = 'font/woff'; '.mp4' = 'video/mp4'; '.webmanifest' = 'application/manifest+json'
}

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
try { $listener.Start() } catch {
    Write-Host "Impossible d'ouvrir le port $Port (deja utilise ?). Fermez l'autre fenetre de test et relancez." -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Site disponible sur http://localhost:$Port/" -ForegroundColor Green
Write-Host "Laissez cette fenetre ouverte pendant le test. Ctrl+C pour arreter."
Write-Host ""
Start-Process "http://localhost:$Port/"

function Send-File($ctx, [string]$file, [int]$status) {
    $ext = [System.IO.Path]::GetExtension($file).ToLowerInvariant()
    $ctx.Response.StatusCode = $status
    $ctx.Response.ContentType = $(if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' })
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $ctx.Response.ContentLength64 = $bytes.Length
    $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
}

try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        try {
            $path = [System.Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath)
            $local = Join-Path $root ($path.TrimStart('/') -replace '/', '\')
            $full = [System.IO.Path]::GetFullPath($local)
            if (-not $full.StartsWith([System.IO.Path]::GetFullPath($root))) { $ctx.Response.StatusCode = 403 }
            elseif ((Test-Path $full -PathType Container) -and -not $path.EndsWith('/')) {
                $ctx.Response.StatusCode = 301
                $ctx.Response.RedirectLocation = $path + '/' + $ctx.Request.Url.Query
            }
            elseif (Test-Path $full -PathType Container) {
                $index = Join-Path $full 'index.html'
                if (Test-Path $index) { Send-File $ctx $index 200 } else { Send-File $ctx (Join-Path $root '404.html') 404 }
            }
            elseif (Test-Path $full -PathType Leaf) { Send-File $ctx $full 200 }
            else { Send-File $ctx (Join-Path $root '404.html') 404 }
            Write-Host ("{0} {1}" -f $ctx.Response.StatusCode, $path)
        } catch {
            try { $ctx.Response.StatusCode = 500 } catch {}
        } finally {
            try { $ctx.Response.OutputStream.Close() } catch {}
        }
    }
} finally {
    $listener.Stop()
}
