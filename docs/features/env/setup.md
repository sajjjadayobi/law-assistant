# Environment Setup Documentation

This document describes the development environment setup for the Law Agent project.

## Prerequisites Installed

### 1. Python
- **Version**: Python 3.9.6
- **Location**: System Python (`python3`)
- **Verified**: ✓

### 2. PostgreSQL
- **Version**: PostgreSQL 14.22 (Homebrew)
- **Status**: Running as a service
- **Installation**: Installed via Homebrew
- **Binary Path**: `/opt/homebrew/opt/postgresql@14/bin/psql`
- **Service**: Started with `brew services start postgresql@14`
- **Default User**: `divar` (current system user)
- **Encoding**: UTF8 (perfect for Persian text)
- **Verified**: ✓

### 3. uv Package Manager
- **Version**: uv 0.8.14
- **Installation**: Already installed via Homebrew
- **Location**: `/opt/homebrew/bin/uv`
- **Verified**: ✓

### 4. Git
- **Status**: Available (repository initialized)
- **Verified**: ✓

## Virtual Environment

A Python virtual environment has been created in the project root:

- **Location**: `.venv/`
- **Python Version**: CPython 3.13.7
- **Created with**: `uv venv`

### Activating the Virtual Environment

```bash
source .venv/bin/activate
```

After activation, your terminal prompt will show `(.venv)` to indicate the environment is active.

### Deactivating the Virtual Environment

```bash
deactivate
```

## PostgreSQL Database Setup

### Connecting to PostgreSQL

Using the full path:
```bash
/opt/homebrew/opt/postgresql@14/bin/psql -l
```

Or add PostgreSQL to your PATH in your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"
```

Then you can use:
```bash
psql -l
```

### Creating the Law Agent Database

The database needs to be created for the project. This will be done in a later task:
```bash
createdb law_agent
```

## Next Steps

With the environment set up, you can proceed to:

1. **Task 0.2**: Study Project Architecture (read design documents)
2. **Task 0.3**: Explore Database Schema (after database creation)
3. **Phase 1**: Database Migration
4. **Phase 2**: Foundation (project structure, dependencies, configuration)

## Important Notes

- **PostgreSQL Deprecation Warning**: PostgreSQL 14 has been deprecated by Homebrew and will be disabled on 2026-11-12. For long-term use, consider upgrading to a newer version.
- **Virtual Environment**: The `.venv/` directory is already in `.gitignore` and will not be committed to the repository.
- **Environment Variables**: Store sensitive information (database passwords, API keys) in a `.env` file, which is also gitignored.

## Quick Reference

| Tool | Version | Command to Verify |
|------|---------|------------------|
| Python | 3.9.6 | `python3 --version` |
| PostgreSQL | 14.22 | `/opt/homebrew/opt/postgresql@14/bin/psql --version` |
| uv | 0.8.14 | `uv --version` |
| Virtual Environment | - | `source .venv/bin/activate` |

## Troubleshooting

### PostgreSQL Not Running

If PostgreSQL service is not running:
```bash
brew services start postgresql@14
```

To check PostgreSQL service status:
```bash
brew services list | grep postgresql
```

### Virtual Environment Issues

If you need to recreate the virtual environment:
```bash
rm -rf .venv
uv venv
```

---

**Setup Completed**: 2026-04-18
**Task**: 0.1 - Environment Setup
