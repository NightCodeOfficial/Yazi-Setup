param(
    [switch]$InstallYazi,
    [switch]$InstallDependencies,
    [switch]$SkipYaziInstallPrompt,
    [switch]$SkipDependencyPrompt,
    [switch]$SkipKeymap,
    [switch]$DryRun,
    [switch]$Force,
    [switch]$Test,
    [switch]$OpenScriptsFolder
)

$ErrorActionPreference = "Stop"

$PackageName = "Yazi Windows Scripts"
$StartMarker = "# >>> Yazi Windows Scripts keybindings >>>"
$EndMarker   = "# <<< Yazi Windows Scripts keybindings <<<"

function Write-Section {
    param([Parameter(Mandatory = $true)][string]$Text)
    Write-Host ""
    Write-Host "=== $Text ===" -ForegroundColor Cyan
}

function Write-Info {
    param([Parameter(Mandatory = $true)][string]$Text)
    Write-Host $Text
}

function Test-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Ask-YesNo {
    param(
        [Parameter(Mandatory = $true)][string]$Question,
        [bool]$DefaultYes = $false
    )

    if ($Force) {
        return $true
    }

    $suffix = "[y/N]"
    if ($DefaultYes) { $suffix = "[Y/n]" }

    while ($true) {
        $answer = Read-Host "$Question $suffix"

        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $DefaultYes
        }

        switch -Regex ($answer.Trim()) {
            "^(y|yes)$" { return $true }
            "^(n|no)$"  { return $false }
            default      { Write-Host "Please answer Y or N." -ForegroundColor Yellow }
        }
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    if ($DryRun -or $Test) {
        Write-Host "[dry-run] $Description" -ForegroundColor DarkGray
        return
    }

    Write-Host $Description
    & $Action
}

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Container) {
        Write-Host "Folder exists: $Path"
        return
    }

    Invoke-Step "Creating folder: $Path" {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Copy-InstallerFile {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        Write-Warning "Missing package file: $Source"
        return
    }

    if ((Test-Path -LiteralPath $Destination -PathType Leaf) -and (-not $Force)) {
        Write-Host "Updating file: $Destination"
    }
    else {
        Write-Host "Copying file: $Destination"
    }

    if (-not ($DryRun -or $Test)) {
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
    }
}

function Install-WingetPackage {
    param([Parameter(Mandatory = $true)][string]$Id)

    if (-not (Test-CommandExists "winget")) {
        Write-Warning "winget is not available. Cannot install $Id."
        return $false
    }

    if ($DryRun -or $Test) {
        Write-Host "[dry-run] winget install --id $Id -e" -ForegroundColor DarkGray
        return $true
    }

    Write-Host "Installing/checking $Id with winget..."
    winget install --id $Id -e --accept-source-agreements --accept-package-agreements

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "winget install failed for $Id. Continuing."
        return $false
    }

    return $true
}

function Add-UserPathIfMissing {
    param([Parameter(Mandatory = $true)][string]$Directory)

    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) {
        return
    }

    $currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ([string]::IsNullOrWhiteSpace($currentUserPath)) {
        $pathParts = @()
    }
    else {
        $pathParts = $currentUserPath -split ";"
    }

    $alreadyExists = $false
    foreach ($part in $pathParts) {
        if ($part.TrimEnd("\") -ieq $Directory.TrimEnd("\")) {
            $alreadyExists = $true
            break
        }
    }

    if ($alreadyExists) {
        Write-Host "User PATH already contains: $Directory"
        return
    }

    if (Ask-YesNo "Add 7-Zip to your user PATH?" $true) {
        Invoke-Step "Adding to user PATH: $Directory" {
            $newPath = $Directory
            if (-not [string]::IsNullOrWhiteSpace($currentUserPath)) {
                $newPath = "$currentUserPath;$Directory"
            }
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            $env:Path = "$env:Path;$Directory"
        }
    }
}

function Get-FoundStatus {
    param([Parameter(Mandatory = $true)][string]$Command)
    if (Test-CommandExists $Command) { return "Found" }
    return "Missing"
}

function Install-KeymapSnippet {
    param(
        [Parameter(Mandatory = $true)][string]$SnippetPath,
        [Parameter(Mandatory = $true)][string]$KeymapPath
    )

    if (-not (Test-Path -LiteralPath $SnippetPath -PathType Leaf)) {
        Write-Warning "Keymap snippet was not found: $SnippetPath"
        return
    }

    if (-not (Ask-YesNo "Add Yazi Windows Scripts keybindings to keymap.toml?" $true)) {
        Write-Host "Skipped keymap update."
        return
    }

    $snippet = Get-Content -LiteralPath $SnippetPath -Raw

    if (Test-Path -LiteralPath $KeymapPath -PathType Leaf) {
        $existing = Get-Content -LiteralPath $KeymapPath -Raw
        $hasStart = $existing.Contains($StartMarker)
        $hasEnd = $existing.Contains($EndMarker)

        if ($hasStart -and $hasEnd) {
            Write-Host "Keymap block already installed. Skipping."
            return
        }

        if ($hasStart -or $hasEnd) {
            Write-Warning "A partial managed keymap block was found in keymap.toml. Please inspect it manually."
            return
        }

        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupPath = "$KeymapPath.backup-$timestamp"

        Invoke-Step "Backing up existing keymap.toml to: $backupPath" {
            Copy-Item -LiteralPath $KeymapPath -Destination $backupPath -Force
        }

        Invoke-Step "Appending Yazi Windows Scripts keybindings to keymap.toml" {
            Add-Content -LiteralPath $KeymapPath -Value "`r`n`r`n$snippet" -Encoding UTF8
        }
    }
    else {
        Invoke-Step "Creating keymap.toml with Yazi Windows Scripts keybindings" {
            Set-Content -LiteralPath $KeymapPath -Value $snippet -Encoding UTF8
        }
    }
}

function Show-TemplateStatus {
    param([Parameter(Mandatory = $true)][string]$TemplateDir)

    $required = @("blank.docx", "blank.xlsx", "blank.pptx")
    foreach ($file in $required) {
        $path = Join-Path $TemplateDir $file
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Write-Host "  [found]   $file" -ForegroundColor Green
        }
        else {
            Write-Host "  [missing] $file" -ForegroundColor Yellow
        }
    }
}

function Show-ToolStatus {
    $tools = @(
        @{ Name = "Yazi"; Command = "yazi" },
        @{ Name = "FFmpeg"; Command = "ffmpeg" },
        @{ Name = "7-Zip"; Command = "7z" },
        @{ Name = "jq"; Command = "jq" },
        @{ Name = "Poppler"; Command = "pdftoppm" },
        @{ Name = "fd"; Command = "fd" },
        @{ Name = "ripgrep"; Command = "rg" },
        @{ Name = "fzf"; Command = "fzf" },
        @{ Name = "zoxide"; Command = "zoxide" },
        @{ Name = "ImageMagick"; Command = "magick" }
    )

    foreach ($tool in $tools) {
        $status = Get-FoundStatus $tool.Command
        if ($status -eq "Found") {
            Write-Host ("  {0}: {1}" -f $tool.Name, $status) -ForegroundColor Green
        }
        else {
            Write-Host ("  {0}: {1}" -f $tool.Name, $status) -ForegroundColor Yellow
        }
    }
}

# Environment checks
Write-Section "Environment checks"

if ($env:OS -ne "Windows_NT") {
    Write-Error "This installer is designed for Windows only."
    exit 1
}

try {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    Write-Host "Running as: $currentIdentity"
    if ($currentIdentity -ieq "NT AUTHORITY\SYSTEM") {
        Write-Error "This installer is running as NT AUTHORITY\SYSTEM. Run it from your normal Windows user account."
        exit 1
    }
}
catch {
    Write-Warning "Could not determine Windows identity. Continuing."
}

$currentDir = (Get-Location).Path
$system32Dir = Join-Path $env:WINDIR "System32"
if ($currentDir.TrimEnd("\") -ieq $system32Dir.TrimEnd("\")) {
    Write-Warning "PowerShell is currently opened in C:\Windows\System32."
    Write-Host "Run this installer from the extracted package folder or launch the included .bat file."
    Read-Host "Press Enter to exit"
    exit 1
}

if ($PSVersionTable.PSEdition -eq "Core") {
    Write-Warning "You are running PowerShell 7+. These scripts are intended to be launched by Windows PowerShell via powershell.exe."
}

$executionPolicy = Get-ExecutionPolicy -Scope CurrentUser
if ($executionPolicy -eq "Restricted") {
    Write-Warning "PowerShell execution policy is Restricted for CurrentUser. The .bat launcher bypasses policy only for this installer run."
}

$InstallerDir = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($InstallerDir)) {
    $InstallerDir = Split-Path -Parent $PSCommandPath
}

if ([string]::IsNullOrWhiteSpace($InstallerDir)) {
    Write-Error "Could not determine installer directory."
    exit 1
}

Write-Host "Installer directory: $InstallerDir"

$UserProfile = [Environment]::GetFolderPath("UserProfile")
if ([string]::IsNullOrWhiteSpace($UserProfile)) {
    Write-Error "Could not determine user profile path."
    exit 1
}

$ScriptsDir = Join-Path $UserProfile "Scripts"
$TemplateDir = Join-Path $UserProfile "User-Templates"
$YaziConfigDir = Join-Path $env:APPDATA "yazi\config"
$YaziFlavorsDir = Join-Path $YaziConfigDir "flavors"
$KeymapPath = Join-Path $YaziConfigDir "keymap.toml"
$PackageScriptsDir = Join-Path $InstallerDir "scripts"
$PackageConfigDir = Join-Path $InstallerDir "yazi-config"
$SnippetPath = Join-Path $PackageConfigDir "keymap-snippet.toml"
$TemplateReadmePath = Join-Path $TemplateDir "README.txt"

Write-Section "Create folders"
Ensure-Directory $ScriptsDir
Ensure-Directory $TemplateDir
Ensure-Directory $YaziConfigDir
Ensure-Directory $YaziFlavorsDir

Write-Section "Copy scripts"
if (Test-Path -LiteralPath $PackageScriptsDir -PathType Container) {
    $scriptFiles = Get-ChildItem -LiteralPath $PackageScriptsDir -Filter "*.ps1" -File
    foreach ($scriptFile in $scriptFiles) {
        $destination = Join-Path $ScriptsDir $scriptFile.Name
        Copy-InstallerFile -Source $scriptFile.FullName -Destination $destination
    }
}
else {
    Write-Warning "Package scripts folder not found: $PackageScriptsDir"
}

Write-Section "Template folder guidance"
$templateReadme = @"
Place blank Office template files in this folder using these exact names:

blank.docx
blank.xlsx
blank.pptx

These are used by the Yazi new-office-file script.

Tip:
Open Word, Excel, or PowerPoint, create a new blank file, then save it here with the required name.
"@

if ((-not (Test-Path -LiteralPath $TemplateReadmePath -PathType Leaf)) -or $Force) {
    Invoke-Step "Writing template README: $TemplateReadmePath" {
        Set-Content -LiteralPath $TemplateReadmePath -Value $templateReadme -Encoding UTF8
    }
}
else {
    Write-Host "Template README already exists: $TemplateReadmePath"
}

Show-TemplateStatus -TemplateDir $TemplateDir

Write-Section "Yazi and dependency checks"
$wingetAvailable = Test-CommandExists "winget"
if (-not $wingetAvailable) {
    Write-Warning "winget was not found. Automatic Yazi/dependency install is unavailable."
}

if (Test-CommandExists "yazi") {
    Write-Host "Yazi found on PATH." -ForegroundColor Green
}
else {
    Write-Warning "Yazi was not found on PATH."
    if ($wingetAvailable) {
        if ($InstallYazi) {
            [void](Install-WingetPackage "sxyazi.yazi")
        }
        elseif (-not $SkipYaziInstallPrompt) {
            if (Ask-YesNo "Install Yazi with winget?" $true) {
                [void](Install-WingetPackage "sxyazi.yazi")
            }
        }
    }
}

$dependencyWingetIds = @(
    "Gyan.FFmpeg",
    "7zip.7zip",
    "jqlang.jq",
    "oschwartz10612.Poppler",
    "sharkdp.fd",
    "BurntSushi.ripgrep.MSVC",
    "junegunn.fzf",
    "ajeetdsouza.zoxide",
    "ImageMagick.ImageMagick"
)

if ($wingetAvailable) {
    if ($InstallDependencies) {
        foreach ($id in $dependencyWingetIds) {
            [void](Install-WingetPackage $id)
        }
    }
    elseif (-not $SkipDependencyPrompt) {
        if (Ask-YesNo "Install recommended Yazi dependencies with winget?" $true) {
            foreach ($id in $dependencyWingetIds) {
                [void](Install-WingetPackage $id)
            }
        }
    }
}

$sevenZipCommonDir = "C:\Program Files\7-Zip"
$sevenZipCommonExe = Join-Path $sevenZipCommonDir "7z.exe"
if (-not (Test-CommandExists "7z")) {
    if (Test-Path -LiteralPath $sevenZipCommonExe -PathType Leaf) {
        Write-Host "7-Zip exists but is not on PATH: $sevenZipCommonExe" -ForegroundColor Yellow
        Add-UserPathIfMissing -Directory $sevenZipCommonDir
    }
    else {
        Write-Warning "7z was not found. Archive extraction will not work until 7-Zip is installed."
    }
}

Write-Section "Yazi keymap"
if ($SkipKeymap) {
    Write-Host "Skipped keymap update because -SkipKeymap was provided."
}
else {
    Install-KeymapSnippet -SnippetPath $SnippetPath -KeymapPath $KeymapPath
}

Write-Section "Final summary"
Write-Host "Scripts folder:"
Write-Host "  $ScriptsDir"
Write-Host ""
Write-Host "Template folder:"
Write-Host "  $TemplateDir"
Write-Host ""
Write-Host "Yazi config folder:"
Write-Host "  $YaziConfigDir"
Write-Host ""
Write-Host "Tool status:"
Show-ToolStatus
Write-Host ""
Write-Host "Template status:"
Show-TemplateStatus -TemplateDir $TemplateDir
Write-Host ""
Write-Host "Next step:"
Write-Host "  Create any missing blank Office template files in the template folder."
Write-Host ""
Write-Host "If newly installed commands are still missing, close and reopen your terminal."

if (-not ($DryRun -or $Test)) {
    if (Test-Path -LiteralPath $TemplateDir -PathType Container) {
        Start-Process explorer.exe $TemplateDir
    }
    if ($OpenScriptsFolder -and (Test-Path -LiteralPath $ScriptsDir -PathType Container)) {
        Start-Process explorer.exe $ScriptsDir
    }
}
