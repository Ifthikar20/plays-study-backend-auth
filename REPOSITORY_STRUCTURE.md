# PlayStudy Repository Structure

## Overview

The PlayStudy project is split into **two separate Git repositories**:

```
PlayStudy Project
├── playstudy-backend      (THIS REPOSITORY)
│   ├── FastAPI application
│   ├── Dockerfile
│   ├── deploy/ scripts
│   └── Database models
│
└── playstudy-card-dash    (SEPARATE REPOSITORY)
    ├── React frontend
    ├── Dashboard UI
    └── Client-side code
```

## This Repository: playstudy-backend

**Location**: `~/Downloads/project-ps-full/playstudy-backend` (or your local path)

### Contains:
- Backend API built with FastAPI
- PostgreSQL database models and migrations
- Redis caching implementation
- JWT authentication
- AI integrations (Claude, DeepSeek)
- Text-to-Speech services
- **Dockerfile** for containerization
- **deploy/** directory with AWS ECS deployment scripts

### Directory Structure:
```
playstudy-backend/
├── app/
│   ├── api/          # API route handlers
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   └── main.py       # FastAPI application
├── deploy/
│   ├── setup-infrastructure.sh  # AWS infrastructure setup
│   ├── deploy.sh                # Deployment script
│   └── ecs-task-definition.json # ECS configuration
├── migrations/       # Alembic database migrations
├── Dockerfile        # Docker container definition
├── requirements.txt  # Python dependencies
└── docker-compose.yml
```

## Frontend Repository: playstudy-card-dash

**Location**: Separate repository

### Contains:
- React frontend application
- Dashboard UI components
- Client-side routing
- API client for backend communication

## Deployment Workflow

### Backend Deployment (from THIS repository)

```bash
# Navigate to backend repository
cd ~/Downloads/project-ps-full/playstudy-backend

# Run deployment scripts
cd deploy
./setup-infrastructure.sh  # First time only
./deploy.sh                 # Each deployment
```

**Why deploy from here?**
- The Dockerfile is in this repository
- Deploy scripts reference backend code and build the Docker image
- ECS task definition points to backend application

### Frontend Deployment (from playstudy-card-dash)

```bash
# Navigate to frontend repository
cd ~/Downloads/project-ps-full/playstudy-card-dash

# Frontend deployment commands go here
# (depends on your frontend hosting: S3, CloudFront, etc.)
```

## Common Mistakes to Avoid

### ❌ DON'T:
- Run backend deployment scripts from the frontend repository
- Expect the Dockerfile to exist in playstudy-card-dash
- Try to deploy both from the same location

### ✅ DO:
- Keep deployment scripts in their respective repositories
- Run backend deployments from playstudy-backend
- Run frontend deployments from playstudy-card-dash
- Verify you're in the correct repository before deploying:
  ```bash
  pwd  # Should show playstudy-backend for backend deployments
  ls Dockerfile  # Should exist in backend repo
  ```

## How They Work Together

```
User Browser
    │
    ├─> Frontend (playstudy-card-dash)
    │   └─> React UI served via S3/CloudFront
    │
    └─> Backend API (playstudy-backend)
        └─> FastAPI on AWS ECS
            ├─> PostgreSQL RDS
            ├─> Redis ElastiCache
            └─> External APIs (Claude, OpenAI, etc.)
```

## Quick Reference

| Task | Repository | Command |
|------|-----------|---------|
| Deploy Backend | playstudy-backend | `cd deploy && ./deploy.sh` |
| Run Backend Locally | playstudy-backend | `uvicorn app.main:app --reload` |
| Database Migration | playstudy-backend | `alembic upgrade head` |
| Deploy Frontend | playstudy-card-dash | (Frontend-specific commands) |
| Run Frontend Locally | playstudy-card-dash | (Frontend-specific commands) |

## Environment Setup

### Backend (.env in playstudy-backend)
```bash
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-key
OPENAI_API_KEY=your-key
```

### Frontend (.env in playstudy-card-dash)
```bash
REACT_APP_API_URL=https://your-backend-api.com
# Other frontend-specific variables
```

## Troubleshooting

### "Dockerfile not found" Error
**Problem**: Running deployment from wrong repository

**Solution**:
```bash
# Check current directory
pwd

# Navigate to backend repository
cd ~/Downloads/project-ps-full/playstudy-backend

# Verify Dockerfile exists
ls -la Dockerfile
```

### "Can't find deploy scripts"
**Problem**: Looking in frontend repository for backend deploy scripts

**Solution**: Backend deployment scripts are in `playstudy-backend/deploy/`

## Contact

For questions about:
- **Backend API, deployment**: Refer to this repository (playstudy-backend)
- **Frontend UI**: Refer to playstudy-card-dash repository
