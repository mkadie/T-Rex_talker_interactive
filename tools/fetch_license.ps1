# Fetch the verbatim PolyForm Noncommercial 1.0.0 license text
# and write it to .\LICENSE, replacing the placeholder.
#
# Run this ONCE, locally, before publishing the repository.
#
# Usage:
#   .\tools\fetch_license.ps1

$ErrorActionPreference = "Stop"

$Url = "https://raw.githubusercontent.com/polyformproject/polyform-licenses/1.0.0/PolyForm-Noncommercial-1.0.0.md"
$Target = "LICENSE"

Write-Host "Fetching PolyForm Noncommercial 1.0.0 from $Url ..."
$body = Invoke-WebRequest -Uri $Url -UseBasicParsing | Select-Object -ExpandProperty Content

if (-not ($body -match "PolyForm Noncommercial")) {
    throw "Fetched content does not look like the PolyForm license."
}

$header = "SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0`r`n`r`n"
[System.IO.File]::WriteAllText((Resolve-Path $Target), $header + $body)

$lineCount = (Get-Content $Target | Measure-Object -Line).Lines
Write-Host "Wrote $Target ($lineCount lines)."
