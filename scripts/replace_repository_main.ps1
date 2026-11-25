# Run from an extracted release folder, with -RepoPath pointing to an existing local Git clone.
param([Parameter(Mandatory=$true)][string]$RepoPath)
$ErrorActionPreference = 'Stop'
$source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$target = (Resolve-Path $RepoPath).Path
if (-not (Test-Path (Join-Path $target '.git'))) { throw 'RepoPath must be a local Git clone with a .git directory.' }
Push-Location $target
try {
  if ((git branch --show-current).Trim() -ne 'main') { throw 'Switch to main before running this script.' }
  if (git status --porcelain) { throw 'Commit or stash local changes first.' }
  git pull --ff-only origin main
  # Remove tracked legacy workflows so they cannot remain after copying new files.
  git rm -r --ignore-unmatch -- '.github/workflows'
  New-Item -ItemType Directory -Force -Path '.github/workflows' | Out-Null
  # Copy full release without touching .git. Also remove untracked legacy YAML workflows.
  Get-ChildItem '.github/workflows' -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in @('.yml','.yaml') } | Remove-Item -Force
  Get-ChildItem $source -Force | Where-Object { $_.Name -ne '.git' } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force
  }
  git add -A
  Write-Host 'Staged repository update. Review with: git status --short'
  Write-Host 'Then run: git commit -m "chore(v4.3.2.17): replace repository and remove legacy workflows"'
  Write-Host 'Then run: git push origin main'
} finally { Pop-Location }
