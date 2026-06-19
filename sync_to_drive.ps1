# =========================================================================
# Snitch Google Drive Sync Script (PowerShell Version)
# =========================================================================

# 1. Dynamically detect the "My Drive" folder to avoid encoding issues
$MyDrive = (Get-ChildItem G:\ | Select-Object -First 1).FullName
$DriveDir = Join-Path $MyDrive "NotebookLM_Sync"

$SpecFile = "s:\00_Apps\01_Projects\Snitch\snitch_spec.md"
$ReadmeFile = "s:\00_Apps\01_Projects\Snitch\README.md"
$CrowdWorksFile = "s:\00_Apps\Crowdsourcing\profile_and_history.md"
$MissionFile = "s:\00_Apps\Crowdsourcing\mission_spec.md"
$HistoryFile = "s:\00_Apps\Crowdsourcing\proposal_history.md"
$RulesFile = "s:\00_Apps\antigravity_rules.txt"
$RemotionReadme = "s:\00_Apps\remotion-shorts\README.md"
$WhisProReadme = "s:\00_Apps\WhisPro-3.0\README.md"
$SpreadsheetReadme = "s:\00_Apps\SpreadSheetBot\README.md"

# 2. Create sync folder if not exists
if (-not (Test-Path $DriveDir)) {
    Write-Host "Creating sync folder: $DriveDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $DriveDir -Force | Out-Null
    Start-Sleep -Seconds 1
}

# 2.5 Clean up legacy files if they exist to avoid clutter
$LegacyFiles = @("README.txt", "profile_and_history.txt", "mission_spec.txt", "scrapebot_spec.md", "README.md", "scrapebot_spec.txt", "scrapebot_readme.txt")
foreach ($file in $LegacyFiles) {
    $filePath = Join-Path $DriveDir $file
    if (Test-Path $filePath) {
        Remove-Item -Path $filePath -Force
    }
}

# 3. Copy files (Explicit destinations with prefix to avoid duplicates)
Write-Host "Syncing files to Google Drive..." -ForegroundColor Cyan
Copy-Item -Path $SpecFile -Destination (Join-Path $DriveDir "snitch_spec.txt") -Force
Copy-Item -Path $ReadmeFile -Destination (Join-Path $DriveDir "snitch_readme.txt") -Force
Copy-Item -Path $CrowdWorksFile -Destination (Join-Path $DriveDir "crowdworks_profile.txt") -Force
Copy-Item -Path $MissionFile -Destination (Join-Path $DriveDir "crowdworks_mission.txt") -Force
Copy-Item -Path $HistoryFile -Destination (Join-Path $DriveDir "crowdworks_history.txt") -Force
Copy-Item -Path $RulesFile -Destination (Join-Path $DriveDir "antigravity_rules.txt") -Force
Copy-Item -Path $RemotionReadme -Destination (Join-Path $DriveDir "remotion_shorts_readme.txt") -Force
Copy-Item -Path $WhisProReadme -Destination (Join-Path $DriveDir "whispro_readme.txt") -Force
Copy-Item -Path $SpreadsheetReadme -Destination (Join-Path $DriveDir "spreadsheet_bot_readme.txt") -Force

Write-Host ">>> Sync Completed!" -ForegroundColor Green
