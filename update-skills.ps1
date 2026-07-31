$ErrorActionPreference = "Stop"

# ============================================================
# Skills Auto-Update Script
# Periodically pulls upstream updates for .claude/skills/
# Usage:  .\update-skills.ps1          - Check & update all
#         .\update-skills.ps1 -DryRun  - Check only, no changes
# ============================================================

$SkillsDir = Join-Path $PSScriptRoot ".claude\skills"
$TempBase  = Join-Path $env:TEMP "skills-update"
$DryRun    = ($args -contains "-DryRun")

# Define each skill's upstream source
$Skills = @(
    [PSCustomObject]@{ Name = "frontend-design"; RepoUrl = "https://github.com/anthropics/claude-code.git"; SubPath = "plugins/frontend-design/skills/frontend-design"; Branch = "main" },
    [PSCustomObject]@{ Name = "find-skills";      RepoUrl = "https://github.com/vercel-labs/skills.git";  SubPath = "skills/find-skills";       Branch = "main" },
    [PSCustomObject]@{ Name = "rtk-develop";      RepoUrl = "https://github.com/rtk-ai/rtk.git";          SubPath = "";                        Branch = "master" }
)

# Helper: run git through cmd /c to avoid PowerShell 5.1 stderr-as-error
function Invoke-Git {
    param([string]$Arguments)
    $tmpFile = [System.IO.Path]::GetTempFileName()
    $exitCode = 1
    try {
        cmd /c "git $Arguments > `"$tmpFile`" 2>&1" 2>$null
        $exitCode = $LASTEXITCODE
        $output = Get-Content $tmpFile -Raw -ErrorAction SilentlyContinue
    }
    finally { Remove-Item $tmpFile -ErrorAction SilentlyContinue }
    return @{ ExitCode = $exitCode; Output = $output }
}

function Get-ShortHash { param([string]$Full) if ($Full -and $Full.Length -ge 8) { $Full.Substring(0,8) } else { $Full } }

Write-Host "========== Skills Auto-Update =========="
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
if ($DryRun) { Write-Host "Mode: DRY RUN (check only, no changes)" }
Write-Host "========================================`n"

if (Test-Path $TempBase) { Remove-Item -Recurse -Force $TempBase }
New-Item -ItemType Directory -Force $TempBase | Out-Null

$Updated  = @()
$UpToDate = @()
$Errors   = @()

foreach ($Skill in $Skills) {
    $Name      = $Skill.Name
    $RepoUrl   = $Skill.RepoUrl
    $SubPath   = $Skill.SubPath
    $Branch    = $Skill.Branch
    $LocalPath = Join-Path $SkillsDir $Name

    Write-Host "[$Name]" -ForegroundColor Cyan
    Write-Host "  upstream: $RepoUrl"
    if ($SubPath) { Write-Host "  subpath : $SubPath" }

    if (-not (Test-Path $LocalPath)) {
        Write-Host "  SKIP: local skill dir not found" -ForegroundColor Yellow
        $Errors += "$Name : local dir missing"
        continue
    }

    try {
        $tmpRepo = Join-Path $TempBase "$Name-repo"

        # Step 1: Get latest upstream commit SHA
        Write-Host "  fetching upstream HEAD..."
        $result = Invoke-Git "ls-remote `"$RepoUrl`" refs/heads/$Branch"
        if ($result.ExitCode -ne 0) { throw "git ls-remote failed: $($result.Output)" }
        $remoteCommit = ($result.Output -split '\s+')[0]
        if (-not $remoteCommit) { throw "could not parse remote commit from: $($result.Output)" }
        Write-Host "  upstream HEAD : $(Get-ShortHash $remoteCommit)"

        # Step 2: Read locally recorded commit
        $lastUpdateFile = Join-Path $LocalPath ".last-update"
        $lastCommit = ""
        if (Test-Path $lastUpdateFile) {
            $lastCommit = (Get-Content $lastUpdateFile -Raw).Trim()
        }

        # Step 3: Compare
        if ($remoteCommit -eq $lastCommit) {
            Write-Host "  status: UP TO DATE" -ForegroundColor Green
            $UpToDate += $Name
            continue
        }

        if (-not $lastCommit) {
            Write-Host "  status: first track (will record current)"
        }
        else {
            Write-Host "  status: UPDATE NEEDED" -ForegroundColor Yellow
            Write-Host "    local : $(Get-ShortHash $lastCommit)"
            Write-Host "    remote: $(Get-ShortHash $remoteCommit)"
        }

        if ($DryRun) {
            Write-Host "  [DRY RUN] skipping actual update" -ForegroundColor Yellow
            continue
        }

        # Step 4: Shallow clone upstream
        Write-Host "  cloning upstream (depth=1)..."
        $result = Invoke-Git "clone --depth 1 --branch `"$Branch`" --single-branch --no-checkout `"$RepoUrl`" `"$tmpRepo`""
        if ($result.ExitCode -ne 0) { throw "git clone failed: $($result.Output)" }

        # Step 5: Sparse checkout
        Push-Location $tmpRepo
        try {
            if ($SubPath) {
                Invoke-Git "sparse-checkout init --cone" | Out-Null
                Invoke-Git "sparse-checkout set `"$SubPath`"" | Out-Null
            }
            Invoke-Git "checkout `"$Branch`"" | Out-Null
        }
        finally { Pop-Location }

        # Step 6: Determine source directory
        if ($SubPath) { $sourceDir = Join-Path $tmpRepo $SubPath }
        else          { $sourceDir = $tmpRepo }

        # Step 7: Backup local version
        $backupDir = Join-Path $TempBase "$Name-backup"
        Write-Host "  backing up local..."
        Copy-Item -Recurse -Force $LocalPath $backupDir

        # Step 8: Sync files (preserve .last-update)
        Write-Host "  syncing files..."
        Get-ChildItem -Path $sourceDir -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($sourceDir.Length + 1)
            if ($relativePath.StartsWith('.git')) { return }
            $destPath = Join-Path $LocalPath $relativePath
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force $destDir | Out-Null }
            Copy-Item -Force $_.FullName $destPath
        }

        # Step 9: Remove local files deleted upstream
        $sourceFiles = @{}
        Get-ChildItem -Path $sourceDir -Recurse -File | ForEach-Object {
            $sourceFiles[$_.FullName.Substring($sourceDir.Length + 1).Replace('\', '/')] = $true
        }
        Get-ChildItem -Path $LocalPath -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($LocalPath.Length + 1).Replace('\', '/')
            if ($rel -eq '.last-update') { return }
            if (-not $sourceFiles.ContainsKey($rel)) {
                Write-Host "  removing stale file: $rel"
                Remove-Item -Force $_.FullName
            }
        }

        # Step 10: Record new commit
        $remoteCommit | Out-File -FilePath $lastUpdateFile -Encoding utf8 -NoNewline

        Write-Host "  done: updated to $(Get-ShortHash $remoteCommit)" -ForegroundColor Green
        $Updated += "$Name -> $(Get-ShortHash $remoteCommit)"
    }
    catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        $Errors += "$Name : $_"

        $backupPath = Join-Path $TempBase "$Name-backup"
        if (Test-Path $backupPath) {
            Write-Host "  restoring backup..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $LocalPath
            Copy-Item -Recurse -Force $backupPath $LocalPath
        }
    }
}

Remove-Item -Recurse -Force $TempBase -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========== Update Report =========="
Write-Host "Updated   : $($Updated.Count)" -ForegroundColor Green
$Updated | ForEach-Object { Write-Host "  + $_" }
Write-Host "Up-to-date: $($UpToDate.Count)" -ForegroundColor Gray
$UpToDate | ForEach-Object { Write-Host "  - $_" }
if ($Errors.Count -gt 0) {
    Write-Host "Errors    : $($Errors.Count)" -ForegroundColor Red
    $Errors | ForEach-Object { Write-Host "  ! $_" }
}
Write-Host "===================================="
