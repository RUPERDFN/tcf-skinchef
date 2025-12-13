# tcf-skinchef

AI Meal Menu Generation Service - A FastAPI service for generating personalized meal menus with strict JSON output and PostgreSQL logging.

## Features

- AI-powered meal menu generation using OpenAI
- Strict JSON output format
- PostgreSQL database logging for all AI requests
- Support for dietary restrictions, allergies, and preferences
- Spanish cuisine focus with budget optimization

## Endpoints

### Health Check

```bash
curl -X GET http://localhost:5000/health
```

Response:
```json
{"ok": true}
```

### Generate Menu

Generate a weekly meal menu based on user preferences.

```bash
curl -X POST http://localhost:5000/menu/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "profile": {
      "budget_eur_week": 50,
      "diners": 4,
      "meals_per_day": 2,
      "days": 7,
      "allergies": ["gluten"],
      "diet": "omnivora",
      "dislikes": ["berenjena"],
      "pantry_text": "tomates, cebolla"
    },
    "days": 7
  }'
```

Response:
```json
{
  "menu": {
    "days": [
      {
        "day": 1,
        "meals": {
          "lunch": {
            "name": "Paella de pollo",
            "ingredients": [
              {"name": "Arroz", "qty": "400g"},
              {"name": "Pollo", "qty": "500g"}
            ],
            "steps": [
              "Cortar el pollo en trozos",
              "Sofreír con aceite de oliva",
              "Añadir el arroz y el caldo"
            ],
            "time_min": 30
          },
          "dinner": {
            "name": "Ensalada mediterránea",
            "ingredients": [
              {"name": "Tomate", "qty": "4 unidades"},
              {"name": "Pepino", "qty": "1 unidad"}
            ],
            "steps": [
              "Cortar las verduras",
              "Aliñar con aceite y vinagre"
            ],
            "time_min": 15
          }
        }
      }
    ]
  },
  "shopping_list": {
    "categories": [
      {
        "name": "Verduras",
        "items": [
          {"name": "Tomate", "qty": "4 unidades"},
          {"name": "Pepino", "qty": "1 unidad"}
        ]
      },
      {
        "name": "Carnes",
        "items": [
          {"name": "Pollo", "qty": "500g"}
        ]
      }
    ]
  }
}
```

### Swap Meal

Replace a specific meal in an existing menu.

```bash
curl -X POST http://localhost:5000/menu/swap \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "profile": {
      "budget_eur_week": 50,
      "diners": 4,
      "meals_per_day": 2,
      "days": 7,
      "allergies": ["gluten"],
      "diet": "omnivora",
      "dislikes": ["berenjena"],
      "pantry_text": "tomates, cebolla"
    },
    "menu": {
      "days": [{"day": 1, "meals": {"lunch": {"name": "Paella", "ingredients": [], "steps": [], "time_min": 30}}}]
    },
    "day_index": 0,
    "meal_key": "lunch",
    "constraints": "quiero algo más ligero"
  }'
```

### Get Substitutions

Get ingredient substitutions based on dietary restrictions.

```bash
curl -X POST http://localhost:5000/substitutions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "profile": {
      "budget_eur_week": 50,
      "diners": 4,
      "meals_per_day": 2,
      "days": 7,
      "allergies": ["gluten"],
      "diet": "omnivora",
      "dislikes": ["berenjena"],
      "pantry_text": ""
    },
    "ingredient": "harina de trigo",
    "reason": "alergia al gluten"
  }'
```

Response:
```json
{
  "substitutions": [
    {"name": "Harina de arroz", "notes": "Usar la misma cantidad, ideal para rebozados"},
    {"name": "Harina de maíz", "notes": "Buena para espesar salsas"},
    {"name": "Harina de almendra", "notes": "Añade sabor a frutos secos, reducir cantidad un 25%"}
  ]
}
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string
- `PORT`: Server port (default: 5000)

## Database Schema

The service logs all AI requests to the `ai_runs` table:

```sql
CREATE TABLE ai_runs (
    id SERIAL PRIMARY KEY,
    kind VARCHAR(50) NOT NULL,
    input_json JSONB NOT NULL,
    output_json JSONB,
    model VARCHAR(100),
    tokens INTEGER,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Running the Service

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:5000/docs
- ReDoc: http://localhost:5000/redoc
