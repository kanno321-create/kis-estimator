# NABERAL Project v0.1.0

## 📋 Overview

NABERAL Project is an advanced AI-powered electrical panel estimation system. This project consolidates core estimation algorithms with modern development practices, dependency management, and comprehensive testing.

## 🎯 Features

- **AI Estimator Engine**: Automated enclosure sizing and breaker placement
- **Thermal Analysis**: Heat dissipation calculation and optimization
- **Phase Balancing**: Automatic load distribution across phases
- **Critic Mode**: AI-powered validation and optimization suggestions
- **Multi-Database Support**: PostgreSQL for production, SQLite for development
- **Excel Integration**: Template-based report generation

## 📦 Project Structure

```
naberal-project/
├── src/
│   └── kis_estimator_core/
│       ├── engine/           # Core algorithms (breaker_placer, enclosure_solver)
│       ├── infra/            # Infrastructure (database, cache)
│       ├── api/              # API layer (future)
│       └── stubs/            # Alternative implementations
├── tests/
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── conftest.py          # Test configuration
├── sql/
│   └── ddl.sql              # Database schema
├── docs/                     # Documentation
├── .github/
│   └── workflows/           # CI/CD pipelines
└── requirements.txt         # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (optional, for production)
- OR-Tools 9.10+ (for optimization)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/kis-company/naberal-project.git
cd naberal-project
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python scripts/init_db.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m regression    # Regression tests
```

### Development

```bash
# Code formatting
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Run all quality checks
npm run quality
```

## 📊 Core Modules

### Engine Components

#### BreakerPlacer
- Optimizes breaker placement within enclosures
- Uses OR-Tools for constraint programming
- Fallback algorithm for environments without OR-Tools

#### EnclosureSolver
- Calculates optimal enclosure dimensions
- Considers IP ratings and door clearances
- Validates thermal constraints

#### EstimateFormatter
- Generates formatted estimates
- Excel template integration
- PDF export capability

### Infrastructure

#### Database
- Dual support for PostgreSQL and SQLite
- Migration management with Alembic
- Connection pooling and health checks

## 🔧 Configuration

### Environment Variables

```env
# Application
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/kis_estimator

# OR-Tools
ORTOOLS_TIMEOUT_SECONDS=30
ORTOOLS_NUM_WORKERS=4

# Feature Flags
ENABLE_AI_ESTIMATOR=true
ENABLE_CRITIC_MODE=true
```

## 📈 Performance

- Breaker placement: < 1 second for up to 100 breakers
- Enclosure solving: < 500ms for standard configurations
- Phase balancing: Maintains < 5% imbalance
- Memory usage: < 500MB for typical workloads

## 🛡️ Security

- Input validation on all endpoints
- SQL injection protection via parameterized queries
- Environment-based configuration
- Audit logging for all changes

## 📝 License

Proprietary - NABERAL Project Team

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📞 Support

For support, please contact the KIS Development Team.

## 🏷️ Version History

<<<<<<< HEAD
- **v0.1.0** (2024-12-29): Initial NABERAL project release with consolidated estimation core




# Claude Code Dev Container (Windows VS Code)

이 템플릿으로 Windows의 VS Code에서 컨테이너 내부에서 **Claude Code**를 안전하게 실행합니다.
YOLO 모드(`--dangerously-skip-permissions`)도 컨테이너 안에서만 사용하세요.

## 0) 사전 준비
- Windows에 **Docker Desktop** 설치(리눅스 컨테이너 모드)
- VS Code 확장: **Dev Containers** 설치

## 1) 사용법(클릭 바이 클릭)
1. 이 폴더를 VS Code로 엽니다.
2. 좌측 하단의 >< 아이콘 클릭 → **Reopen in Container** (또는 `F1` → *Dev Containers: Reopen in Container*).
3. 컨테이너가 뜨면 VS Code 터미널에서 아래 중 하나를 실행:
   - 완전 무인(위험, 컨테이너에서만!):
     ```bash
     claude --dangerously-skip-permissions
     ```
   - 안전 대안(추천):
     ```bash
     # 모든 요청 자동 승인
     claude --permission-mode auto-accept
     # 특정 툴만 자동 승인(화이트리스트)
     claude --permission-mode auto-accept --allowedTools "Read" "Edit" "Bash(git *)"
     ```

## 2) 팁
- 모델 변경: `claude --model sonnet`
- 세션 계속: `claude --continue`
- 도움말: REPL에서 `/help`, `/status`, `/permissions`

## 3) 문제 해결
- 컨테이너 재빌드: `F1` → *Dev Containers: Rebuild Container*
- CLI 최신화: `npm i -g @anthropic-ai/claude-code && claude --version`
- 여전히 퍼미션 프롬프트가 뜨면, 대안 모드로 전환해서 작업 지속하세요.
=======
- **v0.1.0** (2024-12-29): Initial NABERAL project release with consolidated estimation core
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
