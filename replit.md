# tcf-skinchef

## Overview
AI Meal Menu Generation Service built with FastAPI. This service generates personalized weekly meal menus using OpenAI, with strict JSON output formatting and PostgreSQL logging.

## Project Structure
```
.
├── main.py          # FastAPI application with all endpoints
├── README.md        # API documentation with curl examples
├── pyproject.toml   # Python dependencies
└── .gitignore       # Git ignore rules
```

## Key Features
- Health check endpoint
- AI-powered menu generation with dietary restrictions
- Meal swapping within existing menus
- Ingredient substitution suggestions
- PostgreSQL logging of all AI requests

## Endpoints
- `GET /health` - Health check
- `POST /menu/generate` - Generate weekly menu
- `POST /menu/swap` - Swap a specific meal
- `POST /substitutions` - Get ingredient substitutes

## Environment Variables
- `OPENAI_API_KEY` - Required for AI functionality
- `DATABASE_URL` - PostgreSQL connection (auto-configured)

## Running
```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Recent Changes
- 2025-12-13: Initial project setup with all endpoints

## User Preferences
- Spanish language for all recipe content
- Focus on Spanish cuisine
- Budget optimization with common ingredients
- Recipes preferably 20-30 minutes
