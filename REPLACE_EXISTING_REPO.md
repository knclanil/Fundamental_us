# Complete repository replacement (main only)

This is the full v4.3.2.16 project plus a safe replacement helper (package revision v4.3.2.17). It contains **four** `.github/workflows/*.yml` files.

**Uploading a ZIP or copying files over the existing repository does not delete old GitHub Actions YAML files.** You must delete old workflow files from the Git repository and push the deletions.

## Windows PowerShell (recommended)

1. Extract this ZIP to a folder.
2. Clone your repository locally (if needed): `git clone https://github.com/knclanil/MaketData.git`.
3. From the extracted `MaketData-main` folder run:

```powershell
.\scripts\replace_repository_main.ps1 -RepoPath 'C:\path\to\MaketData'
```

4. In your cloned repo, review staged changes: `git status --short`.
5. Commit and push:

```powershell
git commit -m "chore(v4.3.2.17): replace repository and remove legacy workflows"
git push origin main
```

The script refuses to proceed if the clone has uncommitted changes or is not on `main`. It does not delete `.git`, MongoDB data, or historical GitHub Actions runs.

## Verify after pushing

In GitHub > Code > `.github/workflows`, confirm only:

- `collect.yml`
- `blackrock-universe-to-mongodb.yml`
- `largecap-fundamentals.yml`
- `financial-quality-audit.yml`

The Actions history can still show past runs after YAML deletion. Avoid running legacy workflows. Confirm the new sync workflow succeeds before collecting financial data.
