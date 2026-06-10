# A script to move the most recent file of a given type from one directory to another with optional renaming



param (
    [Parameter(Mandatory = $true)][string]$FileType,
    [Parameter(Mandatory = $true)][string]$SourceDirectory,
    [Parameter(Mandatory = $true)][string]$DestinationDirectory,
    [Parameter(Mandatory = $false)][string]$NewFileName
)

function Resolve-Paths {
    if ((Test-Path $SourceDirectory -PathType Container) -and (Test-Path $DestinationDirectory -PathType Container)) {
        return $true
    }
    else {
        return $false
    }
}



function Find-Most-Recent-File-In-Dir {
    $cleanFileType = $FileType.TrimStart(".")
    $filterString = "*." + $cleanFileType 
    $latestFile = Get-ChildItem -Path $SourceDirectory -Filter $filterString -File | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1
    if ($latestFile) {
        return $latestFile
    }
}

function Get-Destination {
    param(
        $sourceFile
    )
    $cleanFileType = $FileType.TrimStart(".")
    
    if ($NewFileName) {
        $destination = Join-Path -Path $DestinationDirectory -ChildPath ($NewFileName+"."+$cleanFileType)
    }
    else {
        $destination = Join-Path -Path $DestinationDirectory -ChildPath $sourceFile.Name
    }
    return $destination
}


function Main {
    if (Resolve-Paths) {
        $sourceFile = Find-Most-Recent-File-In-Dir

        if ($sourceFile) {
            $destination = Get-Destination $sourceFile

            # Check if this would overrite a file
            if (Test-Path $destination -PathType Leaf) {
                $Title = "Confirmation"
                $Message = "The destination file already exists. Do you want to overwrite it?"
                $Options = @(
                    [System.Management.Automation.Host.ChoiceDescription]::new("&Yes", "Overwrite the file")
                    [System.Management.Automation.Host.ChoiceDescription]::new("&No", "Do not overwrite the file")
                )
                $Default = 1
            
                $Choice = $Host.UI.PromptForChoice($Title, $Message, $Options, $Default)
            
                if ($Choice -ne 0) {
                    Write-Host "Cancelled. File was not overwritten." -ForegroundColor Red
                    return
                }

            }


            Move-Item -Path $sourceFile.FullName -Destination $destination -Force
        }
        else {
            Write-Host "No valid source file of the given extension"
        }
    }
    else {
        Write-Host "One or more paths are invalid. Cannot move file."
    }


    
}

Main
