# Suggested Commands for Windows Development

## Testing Commands
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests
pytest -m regression        # Regression tests (20/20 must PASS)

# Run specific test file
pytest tests/unit/test_breaker_placer.py

# Run specific test function
pytest tests/unit/test_breaker_placer.py::test_phase_balance
```

## Code Quality Commands
```bash
# Format code (must run before commit)
black src/ tests/

# Lint and check code quality
ruff check src/ tests/
ruff check --fix src/ tests/      # Auto-fix issues

# Type checking
mypy src/

# Run all quality checks
npm run quality
```

## Database Commands
```bash
# Initialize database
python scripts/init_db.py

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Development Server
```bash
# Start dev server with auto-reload
uvicorn src.kis_estimator_core.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use npm script
npm run dev
```

## Git Workflow (Windows)
```bash
# Check status and branch
git status
git branch

# Create feature branch
git checkout -b feature/[task-name]

# Stage and commit
git add .
git commit -m "feat: description"

# Push to remote
git push origin feature/[task-name]
```

## Windows Utility Commands
```bash
# List files/directories
dir                    # List current directory
dir /s                # List recursively
tree /F               # Show directory tree

# Find files
where python          # Find Python executable
where pytest          # Find pytest executable

# Search file contents (requires grep or Git Bash)
findstr /s "pattern" *.py        # Windows findstr
grep -r "pattern" src/           # Git Bash grep

# Process management
tasklist              # List running processes
taskkill /PID [pid]   # Kill process by PID

# Environment variables
set                   # Show all environment variables
echo %PATH%          # Show PATH variable
```

## Session Workflow
```bash
# 1. Session start
git status && git branch
pytest -m regression              # Verify baseline

# 2. During development
# - Use TodoWrite for task planning
# - Run tests frequently
# - Checkpoint every 30 minutes

# 3. Before commit
black src/ tests/
ruff check src/ tests/
mypy src/
pytest

# 4. Session end
pytest -m regression              # Must pass 20/20
# Create PR only when requested
```