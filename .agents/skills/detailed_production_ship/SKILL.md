---
name: detailed_production_ship
description: Finalize, validate, document, commit, and push changes to main after user approval.
---

# Detailed Production Ship

Use this skill when finalizing a completed code change to document it, validate it, check for regressions, commit with detailed logs, and push it to `main` upon user approval.

## Trigger Phrases
Activate this skill on requests like:
- "detailed production ship"
- "ship this to production"
- "prepare this change for production"
- "finalize and document this work"
- "create/update docs and worklog"
- "check bugs then commit and push"
- "production-ready commit"
- "push to main after docs"

## Core Workflow Steps

### 1. Inspect & Understand Changes
- Execute `git status`.
- Review changed files.
- Read package/config files to identify the stack.
- Identify test, lint, typecheck, build, and format commands from project configuration files (e.g., `package.json`, `Makefile`, `pyproject.toml`, `composer.json`, Docker files, CI configs, or repo docs).
- Do not invent commands when evidence is missing. State assumptions clearly.

### 2. Create or Update Documentation
For every meaningful change, create or update documentation explaining:
- **What** changed
- **Why** it changed
- **Where** it changed
- **How** it works / How to use it
- **Risks** or caveats
- **Rollback** notes if relevant
- **Testing/verification** performed

### 3. Create or Update Daily Worklog
- Filename pattern: `worklog-dd-mm-yyyy.md` (using current local date).
- If a worklog for today already exists, append/update it rather than creating a duplicate.
- Include:
  - Summary
  - Files changed
  - Implementation details
  - Documentation updates
  - Commands/checks run
  - Bugs found and fixes applied
  - Remaining risks
  - Final status

### 4. Bug & Regression Re-check
- Inspect changed code again after documentation updates.
- Look for: syntax issues, missing imports, broken types, bad async/error handling, insecure behavior, migration/config issues, uncommitted generated files, and broken docs references.
- Run safe, read-only verification commands when available.
- If tests fail, diagnose and fix if safe, then rerun verification.
- State any limitations clearly; never claim production-ready unless checks passed or limitations are clearly stated.

### 5. Git Workflow & Commits
- Run `git diff` and `git status` before committing.
- Stage only relevant files.
- Create a detailed commit message with:
  - Concise subject
  - What changed and why
  - Docs/worklog updated
  - Tests/checks run
  - Risks or follow-ups
- Do not commit unrelated files.
- Do not push until showing a final summary and getting explicit approval.
- After approval, push to `main`. If current branch is not `main`, explain the situation before pushing. Fetch and check status of remote/main first to handle divergent history or conflicts gracefully without forcing.
- Never force push unless explicitly requested.

### 6. Response Formatting
Your final response must cover:
- Summary of implementation
- Docs created/updated
- Worklog path
- Bugs/checks performed
- Test/build/lint results
- Commit hash (if committed)
- Push status (if pushed)
- Remaining risks

## Safety & Compliance Rules
- Never hide failed checks or push with failing tests (unless explicitly approved).
- Never include secrets, API keys, tokens, or `.env` files in docs, worklogs, or commits. Stop and warn the user if secrets are detected.
- Ask for confirmation before executing destructive actions.
