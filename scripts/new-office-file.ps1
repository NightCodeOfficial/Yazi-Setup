param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("xlsx", "docx", "pptx")]
    [string]$Type
)

$ErrorActionPreference = 'Stop'

$templateFolder = Join-Path $env:USERPROFILE "User-Templates"

$templateMap = @{
    "xlsx" = @{
        Template = Join-Path $templateFolder "blank.xlsx"
        Label    = "Excel workbook"
    }
    "docx" = @{
        Template = Join-Path $templateFolder "blank.docx"
        Label    = "Word document"
    }
    "pptx" = @{
        Template = Join-Path $templateFolder "blank.pptx"
        Label    = "PowerPoint presentation"
    }
}

$template = $templateMap[$Type].Template
$label = $templateMap[$Type].Label

if (-not (Test-Path -LiteralPath $template -PathType Leaf)) {
    Write-Host "Template not found: $template"
    Read-Host "Press Enter to exit"
    exit 1
}

$name = Read-Host "New $label filename without extension"

if ([string]::IsNullOrWhiteSpace($name)) {
    Write-Host "Cancelled."
    Start-Sleep -Milliseconds 700
    exit
}

# If user typed the extension, remove it so we can add the correct one cleanly.
$name = [System.IO.Path]::GetFileName($name)
if ($name.EndsWith(".$Type", [StringComparison]::OrdinalIgnoreCase)) {
    $name = $name.Substring(0, $name.Length - $Type.Length - 1)
}
if ([string]::IsNullOrWhiteSpace($name) -or $name.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0) {
    throw 'Enter a valid filename.'
}

$targetName = "$name.$Type"
$target = Join-Path (Get-Location) $targetName

if (Test-Path -LiteralPath $target) {
    Write-Host "File already exists: $target"
    Read-Host "Press Enter to exit"
    exit 1
}

[IO.File]::Copy($template, $target, $false)

Write-Host "Created: $target"
Start-Sleep -Milliseconds 700
