# Contributing Guidelines

This document outlines the collaborative engineering workflow for the **Contract & SOW Risk Analyzer** project.

## 1. Branch Structure
- `main`: Production-ready, stable releases only. Never commit or push directly to `main`.
- `develop`: Integration branch for active features. All feature branches merge into `develop`.
- `feature/<owner>-<task>`: Individual developer feature branches (e.g. `feature/sudhansu-auth-jwt`, `feature/pratyush-clause-ocr`).

## 2. Every-Session Workflow
Always sync your local workspace before starting any work:

```bash
# 1. Switch to develop and pull the latest changes
git checkout develop
git pull origin develop

# 2. Create or switch to your feature branch
git checkout -b feature/<your-name>-<task-name>

# 3. Activate virtual environment and ensure dependencies are up to date
# Windows:
.\venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
pip install -r requirements.txt
```

## 3. After-Merge Synchronization
Whenever your teammate merges a PR into `develop`, synchronize immediately:

```bash
git checkout develop
git pull origin develop

# Update backend dependencies
pip install -r requirements.txt

# Update frontend dependencies (if frontend exists)
cd frontend && npm install && cd ..

# Verify complete test suite passes
pytest
```

## 4. Resolving Merge Conflicts
Always resolve merge conflicts on your feature branch, NEVER on `develop`:

```bash
# While on your feature branch:
git fetch origin
git merge origin/develop

# If conflicts occur:
# 1. Open conflicted files and resolve markers.
# 2. Never edit the other developer's code without consulting them.
# 3. If a conflict occurs in shared/contracts.py, halt and review AGENTS.md Section 7.
# 4. Stage and commit resolved files:
git add <resolved-files>
git commit -m "chore(merge): resolve conflicts from develop"

# 5. Run tests to ensure everything is green
pytest

# 6. Push updated feature branch
git push origin feature/<your-name>-<task-name>
```

## 5. End-of-Phase Release (develop -> main)
At the end of each development phase/hackathon milestone:
1. Ensure all feature branches are merged into `develop` and CI is green.
2. Open a Pull Request from `develop` into `main`.
3. Both developers review and approve the release PR.
4. After merging into `main`, tag the release:
   ```bash
   git checkout main
   git pull origin main
   git tag -a phase-1 -m "Release Phase 1: MVP Contract & SOW Risk Analyzer"
   git push origin phase-1
   ```

