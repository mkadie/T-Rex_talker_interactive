# install.ps1 — overlay installer for T-Rex Talker Interactive
#
# Usage:
#   .\install.ps1 -Target C:\path\to\your\trextalkv3
#
# See install.sh for the full description. This script does the same
# thing on Windows PowerShell.

param(
    [Parameter(Mandatory = $true)]
    [string]$Target
)

$ErrorActionPreference = "Stop"
$Src = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path $Target -PathType Container)) {
    Write-Error "target directory does not exist: $Target"
    exit 2
}

foreach ($mandatory in @("code.py", "machine.py", "menus")) {
    if (-not (Test-Path (Join-Path $Target $mandatory))) {
        Write-Warning "'$Target' doesn't contain '$mandatory' - is this really a T-Rex Talker checkout?"
    }
}

Write-Host "Installing T-Rex Talker Interactive overlay into: $Target"
Write-Host ""

function Copy-Tree([string]$RelSrc, [string]$RelDst) {
    $s = Join-Path $Src $RelSrc
    $d = Join-Path $Target $RelDst
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    Write-Host "  copy:   $RelSrc/* -> $RelDst/"
    Copy-Item -Recurse -Force -Path (Join-Path $s '*') -Destination $d
}

Copy-Tree "stim_games" "stim_games"
Copy-Tree "menus" "menus"

$toolsDst = Join-Path $Target "tools"
New-Item -ItemType Directory -Force -Path $toolsDst | Out-Null
Copy-Item -Force -Path (Join-Path $Src "tools\make_trainer_sounds.py") -Destination $toolsDst
Write-Host "  copy:   tools/make_trainer_sounds.py"

Copy-Item -Force -Path (Join-Path $Src "T-Rex_Talker_Subprogram.md") -Destination $Target
Write-Host "  copy:   T-Rex_Talker_Subprogram.md"

Write-Host ""

function Apply-Patch([string]$Rel) {
    $src = Join-Path $Src "upstream_patches\$Rel"
    $dst = Join-Path $Target $Rel
    if (-not (Test-Path $dst)) {
        Write-Host "  new:    $Rel (no upstream file to back up)"
    } else {
        $backup = "$dst.pre_interactive.bak"
        if (-not (Test-Path $backup)) {
            Copy-Item -Force $dst $backup
            Write-Host "  backup: $Rel.pre_interactive.bak"
        } else {
            Write-Host "  backup: already exists, skipping ($Rel.pre_interactive.bak)"
        }
    }
    Copy-Item -Force $src $dst
    Write-Host "  patch:  $Rel"
}

Apply-Patch "action.py"
Apply-Patch "machine.py"
Apply-Patch "config_reader.py"
Apply-Patch "config.txt"
Apply-Patch "menu_system.md"

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  1. Review the changes to your T-Rex Talker checkout."
Write-Host "  2. Run your normal T-Rex Talker installer to flash the device."
Write-Host "  3. (Optional) Generate trainer sound files:"
Write-Host "       python $Target\tools\make_trainer_sounds.py --out $Target\sounds\trainer"
Write-Host "  4. (Optional) Boot into the trainer by adding to $Target\config.txt:"
Write-Host "       mode = stim_games/aac_trainer.py"
