# Telecharge les medias (images, PDF) du site actuel alunites.com
# dans _import\medias-originaux\, en conservant l'arborescence AAAA/MM/fichier.
# Relancable sans risque : les fichiers deja presents et complets sont ignores.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$list   = Join-Path $here 'data\media-a-telecharger.tsv'
$dest   = Join-Path $here 'medias-originaux'
$log    = Join-Path $here 'telechargement-log.txt'

if (-not (Test-Path $list)) { Write-Host "Liste introuvable : $list" -ForegroundColor Red; exit 1 }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
"Debut : $(Get-Date -Format s)" | Out-File -FilePath $log -Encoding utf8

$rows  = Get-Content -Path $list -Encoding UTF8 | Where-Object { $_.Trim() -ne '' }
$total = $rows.Count
$ok = 0; $skip = 0; $fail = 0; $i = 0
$client = New-Object System.Net.WebClient
$client.Headers.Add('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Alunites-migration')

foreach ($row in $rows) {
    $i++
    $parts = $row -split "`t"
    $url = $parts[0]; $rel = $parts[1]; $expected = [int64]$parts[2]
    $target = Join-Path $dest ($rel -replace '/', '\')
    $dir = Split-Path -Parent $target
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

    if ((Test-Path $target) -and ((Get-Item $target).Length -gt 0)) {
        $skip++
        continue
    }
    Write-Host ("[{0}/{1}] {2}" -f $i, $total, $rel)
    $done = $false
    for ($try = 1; $try -le 3 -and -not $done; $try++) {
        try {
            $tmp = "$target.part"
            $client.DownloadFile($url, $tmp)
            Move-Item -Force $tmp $target
            $done = $true
            $ok++
        } catch {
            Start-Sleep -Seconds (2 * $try)
            if ($try -eq 3) {
                $fail++
                "ECHEC`t$url`t$($_.Exception.Message)" | Out-File -FilePath $log -Append -Encoding utf8
                Write-Host "   echec : $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
}

$summary = "Termine : $ok telecharges, $skip deja presents, $fail echecs (total $total)"
$summary | Out-File -FilePath $log -Append -Encoding utf8
Write-Host ""
Write-Host $summary -ForegroundColor Green
Write-Host "Journal : $log"
