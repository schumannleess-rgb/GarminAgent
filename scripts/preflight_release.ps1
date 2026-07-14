[CmdletBinding()]
param(
    [string] $RepoRoot
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
Set-Location -LiteralPath $RepoRoot

$failures = @()

function Add-Failure {
    param([string] $Message)
    $script:failures += $Message
}

if (-not (Test-Path -LiteralPath ".git")) {
    Add-Failure "Not a Git repository root: $RepoRoot"
}

$tracked = git ls-files

$sensitivePathPattern = '(^|/)(\.env|\.local|tokens|cache|data|logs|memory|output)(/|$)|garmin_tokens\.json$|\.token$|\.bak$|daily_health\.json$'
$trackedSensitive = $tracked | Where-Object { $_ -match $sensitivePathPattern }
if ($trackedSensitive) {
    Add-Failure "Tracked runtime/sensitive paths:`n  $($trackedSensitive -join "`n  ")"
}

$secretPattern = '(GARMIN_PASSWORD\s*=\s*(?!your_|$).+|ANTHROPIC_AUTH_TOKEN\s*=\s*(?!your_|$).+|ZHIPU_API_KEY\s*=\s*(?!your_|$).+|access_token["'']?\s*[:=]\s*["''][A-Za-z0-9._~\-]{16,}|refresh_token["'']?\s*[:=]\s*["''][A-Za-z0-9._~\-]{16,}|Bearer\s+[A-Za-z0-9._~\-]{16,})'
$secretHits = @()
foreach ($file in $tracked) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        continue
    }
    $matches = Select-String -LiteralPath $file -Pattern $secretPattern -AllMatches -ErrorAction SilentlyContinue
    foreach ($match in $matches) {
        $secretHits += "${file}:$($match.LineNumber)"
    }
}
if ($secretHits) {
    Add-Failure "Possible secret values in tracked files:`n  $($secretHits -join "`n  ")"
}

$ignoredRuntime = @(".local", ".env", "tokens", "cache", "data", "logs", "memory", "output")
foreach ($path in $ignoredRuntime) {
    if (Test-Path -LiteralPath $path) {
        $ignored = git check-ignore -q $path
        if ($LASTEXITCODE -ne 0) {
            Add-Failure "Runtime path is not ignored by Git: $path"
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "Release preflight failed:" -ForegroundColor Red
    foreach ($failure in $failures) {
        Write-Host ""
        Write-Host $failure -ForegroundColor Red
    }
    exit 1
}

Write-Host "Release preflight passed." -ForegroundColor Green
exit 0
