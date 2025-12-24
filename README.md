# PlayStudy Backend API

FastAPI-based backend for the PlayStudy Card Dashboard application.

## Features

- ✅ FastAPI with async support
- ✅ PostgreSQL with SQLAlchemy ORM
- ✅ Redis caching
- ✅ JWT authentication
- ✅ AI integrations (Anthropic Claude, DeepSeek)
- ✅ Text-to-Speech (OpenAI, Google Cloud)
- ✅ Rate limiting
- ✅ Field-level encryption
- ✅ Comprehensive API documentation

## Quick Start

### Local Development

1. **Install dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set up environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run database migrations:**
```bash
alembic upgrade head
```

4. **Start the server:**
```bash
uvicorn app.main:app --reload --port 8000
```

5. **Access API documentation:**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Docker Development

```bash
docker build -t playstudy-backend .
docker run -p 8000:8000 --env-file .env playstudy-backend
```

## AWS Deployment

See [AWS_ECS_DEPLOYMENT_GUIDE.md](./AWS_ECS_DEPLOYMENT_GUIDE.md) for complete deployment instructions.

**Quick deploy:**
```bash
cd deploy
./setup-infrastructure.sh  # One-time setup
./deploy.sh                 # Deploy application
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Study Sessions
- `GET /api/app-data` - Get all app data
- `POST /api/study-sessions/create-with-ai` - Create session with AI
- `GET /api/study-sessions/{id}` - Get session details
- `PATCH /api/study-sessions/{id}/topics/{topic_id}/progress` - Update progress

### Text-to-Speech
- `POST /api/tts/generate` - Generate speech
- `GET /api/tts/providers` - Get available providers

See full API documentation at `/api/docs` when running.

## Architecture

```
FastAPI Application
    ├── PostgreSQL (RDS)
    ├── Redis (ElastiCache)
    ├── Anthropic Claude API
    ├── OpenAI TTS API
    └── Google Cloud TTS API
```

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://host:6379/0

# Security
SECRET_KEY=your-secret-key
FIELD_ENCRYPTION_KEY=your-encryption-key

# API Keys
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
GOOGLE_CLOUD_API_KEY=your-key
RECAPTCHA_SECRET_KEY=your-key
```

## Database Schema

See `app/models/` for complete schema:
- `User` - User accounts and profiles
- `StudySession` - Study sessions
- `Topic` - Topics and subtopics
- `Question` - Questions and answers
- `Folder` - Folder organization
- `Game` - Educational games

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## Performance

- **Smart batching**: 90% reduction in API calls
- **Query optimization**: 5-6 queries per request (was 30+)
- **Redis caching**: 80% database load reduction
- **Rate limiting**: Prevents abuse

See [COST_ANALYSIS.md](./COST_ANALYSIS.md) for detailed performance metrics.

## Cost

Estimated monthly cost for 10,000 users: **$485-715**

See [COST_ANALYSIS.md](./COST_ANALYSIS.md) for breakdown.

## Documentation

- [AWS Deployment Guide](./AWS_ECS_DEPLOYMENT_GUIDE.md)
- [Cost Analysis](./COST_ANALYSIS.md)
- [Progress Batching](./PROGRESS_BATCHING.md)

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0+
- **Authentication**: JWT (python-jose)
- **Deployment**: AWS ECS Fargate

## License

[Your License]

## Support

For issues and questions, see the main repository.
