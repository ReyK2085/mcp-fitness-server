import json
import os
import time
from pathlib import Path
from fastapi import FastAPI, APIRouter
from fastmcp import FastMCP
from pydantic import BaseModel
import uvicorn
from utils.logging_utils import build_log_config

PORT = 8003
LOG_FILE = Path("logs/mcp_log_streamable_http.log")
LOG_CONFIG = build_log_config(
    LOG_FILE,
    logger_handlers={
        "uvicorn": ["rotating_file", "console"],
        "uvicorn.error": ["rotating_file", "console"],
        "uvicorn.access": ["rotating_file"],
    },
    root_level="INFO",
    logger_level="DEBUG",
)

# FastAPI app setup
app = FastAPI(
    title="Personal Fitness Assistant MCP Server",
    description="API endpoints auto-exposed as MCP tools via FastMCP, with resources and prompts.",
    version="1.0.0",
)

# ==========================================
# 1. TOOLS (FastAPI Endpoints)
# ==========================================
# Data Models for validation
class WorkoutItem(BaseModel):
    exercise: str
    sets: int
    reps: int
    weight_kg: float

class NutritionItem(BaseModel):
    food_item: str

@app.post("/log-exercise")
def log_exercise(workout: WorkoutItem):
    """Saves structured exercise data (sets, reps, weight) to the user's history."""
    file_path = "workout_history.json"
    
    # Load existing history
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    else:
        history = []
        
    # Append new log
    history.append(workout.model_dump())
    
    with open(file_path, "w") as f:
        json.dump(history, f, indent=4)
        
    return {"status": "success", "message": f"Logged {workout.exercise} successfully."}

@app.post("/analyze-nutrition")
def analyze_nutrition(item: NutritionItem):
    """Fetches caloric and macronutrient data for identified food items."""
    # Mock data lookup for nutrition analysis
    food_db = {
        "toast": {"calories": 150, "protein": 4, "carbs": 25, "fat": 2},
        "cheese": {"calories": 110, "protein": 7, "carbs": 1, "fat": 9},
        "bread": {"calories": 80, "protein": 3, "carbs": 15, "fat": 1},
        "peanut butter": {"calories": 190, "protein": 8, "carbs": 6, "fat": 16}
    }
    
    food_name = item.food_item.lower()
    if food_name in food_db:
        return {"food": food_name, "macros": food_db[food_name]}
    return {"food": food_name, "macros": "unknown", "message": "Item not found in database. Estimating standard values."}


# Initialize FastMCP from the FastAPI configuration
mcp = FastMCP.from_fastapi(
    app,
    name="Personal Fitness Assistant Server",
    instructions="Fitness tracking tools with supporting resources and prompts.",
)

# ==========================================
# 2. RESOURCES
# ==========================================
@mcp.resource("resource://workout_history", name="Workout History Log", mime_type="application/json")
def _resource_workout_history():
    """A dynamic record of all previously logged exercises."""
    file_path = "workout_history.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    return "[]"

@mcp.resource("resource://macro_targets", name="Daily Macro Targets", mime_type="application/json")
def _resource_macro_targets():
    """A static resource defining the user's daily protein, carb, and fat goals."""
    # Ensure this file exists or return text directly
    targets = {"daily_targets": {"protein_g": 160, "carbs_g": 200, "fat_g": 70}}
    return json.dumps(targets, indent=4)


# ==========================================
# 3. PROMPTS
# ==========================================
@mcp.prompt(name="parse_workout", description="Takes a text input of a workout and structures it into JSON for logging.")
def _prompt_parse_workout(input_text: str) -> str:
    return f"""Analyze the following text description of a workout. 
Extract the exercise name, number of sets, repetitions, and weight. 
Format the output strictly as a JSON object matching the parameters of the log_exercise tool.

Input: {input_text}"""

@mcp.prompt(name="parse_macros", description="Takes a text description of a meal and identifies food items and estimated portions.")
def _prompt_parse_macros(input_text: str) -> str:
    return f"""Extract food items and approximate quantities from this meal description. 
Convert natural language quantities (e.g., 'two slices', 'a tablespoon') into standardized units for the analyze_nutrition tool.

Input: {input_text}"""


# Mount onto FastAPI for HTTP/SSE transport modes
mcp_http_app = mcp.http_app(path="/", transport="streamable-http")
mcp_sse_app = mcp.http_app(path="/", transport="sse")
app.router.lifespan_context = mcp_http_app.lifespan

app.mount("/mcp", mcp_http_app)
app.mount("/sse", mcp_sse_app)

if __name__ == "__main__":
    print("Starting Personal Fitness Assistant Server (HTTP + MCP)...")
    uvicorn.run(
        app,
        host="localhost",
        port=PORT,
        log_level="trace",
        log_config=LOG_CONFIG,
    )