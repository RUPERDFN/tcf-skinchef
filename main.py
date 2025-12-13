import os
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI

app = FastAPI(title="tcf-skinchef", description="AI Meal Menu Generation Service")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Eres un chef experto español que crea menús semanales personalizados. Debes seguir estas reglas ESTRICTAMENTE:

REGLAS ABSOLUTAS (NUNCA violar):
1. ALERGIAS: NUNCA incluir ingredientes que contengan alérgenos especificados. Esto es ABSOLUTO y no negociable.
2. DIETA: Siempre respetar el tipo de dieta (omnívora, vegetariana, vegana, etc.)
3. DISGUSTOS: Nunca incluir ingredientes que el usuario ha indicado que no le gustan.

PREFERENCIAS:
4. PRESUPUESTO: Optimizar usando ingredientes españoles comunes y económicos.
5. TIEMPO: Preferir recetas de 20-30 minutos de preparación.
6. VARIEDAD: Evitar repetir platos durante la semana.
7. DESPENSA: Aprovechar ingredientes que el usuario ya tiene en su despensa.

FORMATO DE SALIDA:
- Responde ÚNICAMENTE con JSON válido, sin texto explicativo.
- Sigue exactamente el esquema JSON solicitado.
- Todos los textos deben estar en español."""


def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)


def log_ai_run(kind: str, input_json: dict, output_json: dict = None, model: str = None, tokens: int = None, error: str = None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO ai_runs (kind, input_json, output_json, model, tokens, error) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (kind, json.dumps(input_json), json.dumps(output_json) if output_json else None, model, tokens, error)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error logging AI run: {e}")


class ProfileModel(BaseModel):
    budget_eur_week: float = Field(..., description="Weekly budget in EUR")
    diners: int = Field(..., description="Number of diners")
    meals_per_day: int = Field(..., description="Number of meals per day")
    days: int = Field(..., description="Number of days to plan")
    allergies: list[str] = Field(default=[], description="List of allergies")
    diet: str = Field(..., description="Diet type (omnivora, vegetariana, vegana, etc.)")
    dislikes: list[str] = Field(default=[], description="Disliked ingredients")
    pantry_text: str = Field(default="", description="Available pantry items")


class MenuGenerateRequest(BaseModel):
    user_id: str
    profile: ProfileModel
    days: int


class Ingredient(BaseModel):
    name: str
    qty: str


class Meal(BaseModel):
    name: str
    ingredients: list[Ingredient]
    steps: list[str]
    time_min: int


class DayMeals(BaseModel):
    lunch: Optional[Meal] = None
    dinner: Optional[Meal] = None
    breakfast: Optional[Meal] = None


class DayMenu(BaseModel):
    day: int
    meals: DayMeals


class ShoppingItem(BaseModel):
    name: str
    qty: str


class ShoppingCategory(BaseModel):
    name: str
    items: list[ShoppingItem]


class ShoppingList(BaseModel):
    categories: list[ShoppingCategory]


class MenuOutput(BaseModel):
    days: list[DayMenu]


class MenuResponse(BaseModel):
    menu: MenuOutput
    shopping_list: ShoppingList


class MenuSwapRequest(BaseModel):
    user_id: str
    profile: ProfileModel
    menu: dict
    day_index: int
    meal_key: str
    constraints: Optional[str] = None


class SubstitutionRequest(BaseModel):
    user_id: str
    profile: ProfileModel
    ingredient: str
    reason: str


class Substitution(BaseModel):
    name: str
    notes: str


class SubstitutionResponse(BaseModel):
    substitutions: list[Substitution]


@app.get("/health")
def health_check():
    return {"ok": True}


@app.post("/menu/generate", response_model=MenuResponse)
def generate_menu(request: MenuGenerateRequest):
    input_data = request.model_dump()
    
    user_prompt = f"""Genera un menú para {request.days} días con las siguientes especificaciones:

Perfil del usuario:
- Presupuesto semanal: {request.profile.budget_eur_week}€
- Número de comensales: {request.profile.diners}
- Comidas por día: {request.profile.meals_per_day}
- Alergias: {', '.join(request.profile.allergies) if request.profile.allergies else 'Ninguna'}
- Dieta: {request.profile.diet}
- Ingredientes que no le gustan: {', '.join(request.profile.dislikes) if request.profile.dislikes else 'Ninguno'}
- Ingredientes en despensa: {request.profile.pantry_text if request.profile.pantry_text else 'No especificado'}

Responde con el siguiente formato JSON exacto:
{{
  "menu": {{
    "days": [
      {{
        "day": 1,
        "meals": {{
          "lunch": {{
            "name": "Nombre del plato",
            "ingredients": [{{"name": "ingrediente", "qty": "cantidad"}}],
            "steps": ["paso 1", "paso 2"],
            "time_min": 25
          }},
          "dinner": {{
            "name": "Nombre del plato",
            "ingredients": [{{"name": "ingrediente", "qty": "cantidad"}}],
            "steps": ["paso 1", "paso 2"],
            "time_min": 20
          }}
        }}
      }}
    ]
  }},
  "shopping_list": {{
    "categories": [
      {{
        "name": "Verduras",
        "items": [{{"name": "Tomate", "qty": "4 unidades"}}]
      }}
    ]
  }}
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        output_text = response.choices[0].message.content
        output_json = json.loads(output_text)
        tokens_used = response.usage.total_tokens if response.usage else None
        
        log_ai_run(
            kind="menu_generate",
            input_json=input_data,
            output_json=output_json,
            model="gpt-4o-mini",
            tokens=tokens_used
        )
        
        return output_json
        
    except json.JSONDecodeError as e:
        log_ai_run(kind="menu_generate", input_json=input_data, error=f"JSON parse error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error parsing AI response")
    except Exception as e:
        log_ai_run(kind="menu_generate", input_json=input_data, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/menu/swap", response_model=MenuResponse)
def swap_meal(request: MenuSwapRequest):
    input_data = request.model_dump()
    
    user_prompt = f"""Necesito reemplazar una comida en el menú existente.

Menú actual: {json.dumps(request.menu, ensure_ascii=False)}

Reemplazar: Día {request.day_index + 1}, comida "{request.meal_key}"
Restricciones adicionales: {request.constraints if request.constraints else 'Ninguna'}

Perfil del usuario:
- Presupuesto semanal: {request.profile.budget_eur_week}€
- Número de comensales: {request.profile.diners}
- Alergias: {', '.join(request.profile.allergies) if request.profile.allergies else 'Ninguna'}
- Dieta: {request.profile.diet}
- Ingredientes que no le gustan: {', '.join(request.profile.dislikes) if request.profile.dislikes else 'Ninguno'}

Devuelve el menú completo actualizado con la nueva comida y la lista de compras actualizada.
Usa el mismo formato JSON que el menú original."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        output_text = response.choices[0].message.content
        output_json = json.loads(output_text)
        tokens_used = response.usage.total_tokens if response.usage else None
        
        log_ai_run(
            kind="menu_swap",
            input_json=input_data,
            output_json=output_json,
            model="gpt-4o-mini",
            tokens=tokens_used
        )
        
        return output_json
        
    except json.JSONDecodeError as e:
        log_ai_run(kind="menu_swap", input_json=input_data, error=f"JSON parse error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error parsing AI response")
    except Exception as e:
        log_ai_run(kind="menu_swap", input_json=input_data, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/substitutions", response_model=SubstitutionResponse)
def get_substitutions(request: SubstitutionRequest):
    input_data = request.model_dump()
    
    user_prompt = f"""Necesito sustitutos para un ingrediente.

Ingrediente a sustituir: {request.ingredient}
Razón: {request.reason}

Perfil del usuario:
- Alergias: {', '.join(request.profile.allergies) if request.profile.allergies else 'Ninguna'}
- Dieta: {request.profile.diet}
- Ingredientes que no le gustan: {', '.join(request.profile.dislikes) if request.profile.dislikes else 'Ninguno'}

Proporciona 3-5 sustitutos válidos que respeten las alergias y dieta del usuario.

Responde con el siguiente formato JSON:
{{
  "substitutions": [
    {{"name": "nombre del sustituto", "notes": "notas sobre cómo usarlo"}}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        output_text = response.choices[0].message.content
        output_json = json.loads(output_text)
        tokens_used = response.usage.total_tokens if response.usage else None
        
        log_ai_run(
            kind="substitutions",
            input_json=input_data,
            output_json=output_json,
            model="gpt-4o-mini",
            tokens=tokens_used
        )
        
        return output_json
        
    except json.JSONDecodeError as e:
        log_ai_run(kind="substitutions", input_json=input_data, error=f"JSON parse error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error parsing AI response")
    except Exception as e:
        log_ai_run(kind="substitutions", input_json=input_data, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)
