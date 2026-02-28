# CLAUDE.md

This file provides guidance to AI assistants (Claude and others) working with this repository.

## Project Overview

**progetto-1** is a newly initialized repository currently in early setup phase. As of the last update, no application code, framework, or dependency configuration has been added yet. This document will grow as the project evolves.

- **Owner:** fabiobianconi3-cmyk
- **Remote:** `http://local_proxy@127.0.0.1:54380/git/fabiobianconi3-cmyk/progetto-1`

## Repository Structure

```
progetto-1/
├── README.md       # Project title placeholder
└── CLAUDE.md       # This file
```

This structure is expected to expand significantly as the project is built out.

## Git Workflow

### Branch Naming

- Main line: `master`
- Claude-generated branches follow the pattern: `claude/<task-slug>-<session-id>`

### Commits

- Commit messages should be descriptive and written in imperative mood (e.g., "Add authentication module", not "Added auth")
- Commits are signed using SSH key at `/home/claude/.ssh/commit_signing_key.pub`
- Never amend published commits — create new ones instead

### Pushing

Always push with tracking:
```bash
git push -u origin <branch-name>
```

Claude feature branches must start with `claude/` and end with the matching session ID, otherwise the push will be rejected with HTTP 403.

## Development Conventions (To Be Established)

No technology stack has been selected yet. When the stack is chosen, this section should document:

- Language and runtime version
- Dependency management commands (install, add, remove)
- Build commands
- Test commands and how to run a subset of tests
- Linting and formatting commands
- How to start a local development server

## Working with This Codebase

### Before Making Changes

1. Check the current branch: `git status`
2. Ensure you are on the correct feature branch
3. Read any relevant existing files before modifying them

### Adding New Features

1. Create a branch following the naming convention above
2. Make focused, atomic commits
3. Push to the feature branch — never directly to `master`

### What to Avoid

- Do not push to `master` directly
- Do not commit sensitive data (credentials, secrets, `.env` files)
- Do not add unnecessary abstractions or over-engineer early-stage code
- Do not create files that are not needed for the current task

## Updating This File

Update CLAUDE.md whenever:
- A technology stack is chosen and configured
- New development commands or workflows are established
- Code conventions are decided
- Architecture decisions are made
- New integrations (databases, APIs, CI/CD) are added
