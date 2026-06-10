param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("xlsx", "docx", "pptx")]
    [string]$Type
)

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

if (-not (Test-Path $template)) {
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
$name = [System.IO.Path]::GetFileNameWithoutExtension($name)

$targetName = "$name.$Type"
$target = Join-Path (Get-Location) $targetName

if (Test-Path $target) {
    Write-Host "File already exists: $target"
    Read-Host "Press Enter to exit"
    exit 1
}

Copy-Item $template $target

Write-Host "Created: $target"
Start-Sleep -Milliseconds 700
