[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string] $RuntimeDir = ".local"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$runtime = Join-Path $repo $RuntimeDir

function Resolve-InRepo {
    param([string] $Path)
    $full = [System.IO.Path]::GetFullPath((Join-Path $repo $Path))
    if (-not $full.StartsWith($repo, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing path outside repo: $Path"
    }
    return $full
}

function Move-IfPresent {
    param(
        [string] $Source,
        [string] $Destination
    )

    $src = Resolve-InRepo $Source
    if (-not (Test-Path -LiteralPath $src)) {
        return
    }

    $dst = Resolve-InRepo $Destination
    if (Test-Path -LiteralPath $dst) {
        Write-Host "Skip existing destination: $Destination" -ForegroundColor Yellow
        return
    }

    $parent = Split-Path -Parent $dst
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    if ($PSCmdlet.ShouldProcess($src, "Move to $dst")) {
        Move-Item -LiteralPath $src -Destination $dst
        Write-Host "Moved $Source -> $Destination"
    }
}

New-Item -ItemType Directory -Force -Path $runtime | Out-Null

Move-IfPresent ".env" "$RuntimeDir/.env"
Move-IfPresent "tokens" "$RuntimeDir/tokens"
Move-IfPresent "cache" "$RuntimeDir/cache"
Move-IfPresent "data" "$RuntimeDir/data"
Move-IfPresent "logs" "$RuntimeDir/logs"
Move-IfPresent "memory" "$RuntimeDir/memory"
Move-IfPresent "output" "$RuntimeDir/output"

$privateDocs = Join-Path $runtime "private-docs"
New-Item -ItemType Directory -Force -Path $privateDocs | Out-Null
foreach ($doc in Get-ChildItem -LiteralPath (Join-Path $repo "docs") -File -ErrorAction SilentlyContinue) {
    if ($doc.Name -match '\.(json|token)$') {
        $dst = Join-Path $privateDocs $doc.Name
        if (-not (Test-Path -LiteralPath $dst) -and $PSCmdlet.ShouldProcess($doc.FullName, "Move to $dst")) {
            Move-Item -LiteralPath $doc.FullName -Destination $dst
            Write-Host "Moved docs/$($doc.Name) -> $RuntimeDir/private-docs/$($doc.Name)"
        }
    }
}

Write-Host "Runtime migration complete. Review $RuntimeDir before deleting external backups."
