$ErrorActionPreference = "Stop"

function Pause-Return {
    Write-Host ""
    Read-Host "Press Enter to return to Yazi"
}

$TempFile = Join-Path $env:TEMP "archive_to_decompress.txt"

if (-not (Test-Path -LiteralPath $TempFile)) {
    Write-Host "Temp archive file was not found:"
    Write-Host $TempFile
    Pause-Return
    exit 1
}

$ArchiveUrl = Get-Content -LiteralPath $TempFile -Raw
$ArchiveUrl = $ArchiveUrl.Trim()

if ([string]::IsNullOrWhiteSpace($ArchiveUrl)) {
    Write-Host "Temp archive file was empty."
    Pause-Return
    exit 1
}

try {
    if ($ArchiveUrl -match '^file:') {
        $ArchivePath = ([System.Uri]$ArchiveUrl).LocalPath
    }
    else {
        $ArchivePath = $ArchiveUrl
    }
}
catch {
    Write-Host "Could not convert archive URL to path:"
    Write-Host $ArchiveUrl
    Pause-Return
    exit 1
}

if (-not (Test-Path -LiteralPath $ArchivePath)) {
    Write-Host "Archive path not found:"
    Write-Host $ArchivePath
    Pause-Return
    exit 1
}

$ArchivePath = (Resolve-Path -LiteralPath $ArchivePath).Path
$ArchiveDir = [System.IO.Path]::GetDirectoryName($ArchivePath)
$ArchiveName = [System.IO.Path]::GetFileNameWithoutExtension($ArchivePath)
$OutputDir = Join-Path $ArchiveDir $ArchiveName

Write-Host ""
Write-Host "Archive:"
Write-Host "  $ArchivePath"
Write-Host ""
Write-Host "Extract to:"
Write-Host "  $OutputDir"
Write-Host ""

$Confirm = Read-Host "Extract? [y/N]"

if ($Confirm -notmatch '^(y|yes)$') {
    Write-Host "Cancelled."
    Start-Sleep -Seconds 1
    exit 0
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$SevenZip = Get-Command 7z -ErrorAction SilentlyContinue
if ($SevenZip) {
    $SevenZipPath = $SevenZip.Source
}
else {
    $CommonSevenZipPath = "C:\Program Files\7-Zip\7z.exe"
    if (Test-Path -LiteralPath $CommonSevenZipPath -PathType Leaf) {
        $SevenZipPath = $CommonSevenZipPath
    }
    else {
        Write-Host "7-Zip was not found. Install 7-Zip or add 7z.exe to PATH."
        Pause-Return
        exit 1
    }
}

& $SevenZipPath x "$ArchivePath" "-o$OutputDir" -y

Write-Host ""
Write-Host "Extracted to:"
Write-Host "  $OutputDir"

Pause-Return
