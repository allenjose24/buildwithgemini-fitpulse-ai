# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

import google.auth
from google.auth.transport.requests import Request
from google.cloud import firestore

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback

# Hardcoded Project ID string (do NOT use google.auth.default or env vars)
PROJECT_ID = "qwiklabs-gcp-03-a9a784fdfd5f"
AGENT_ENGINE_RESOURCE_NAME = (
    "projects/1067804430983/locations/us-east1/reasoningEngines/4175445984014237696"
)

a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = a2ui_schema_manager.generate_system_prompt(
    role_description=(
        "You are FitPulse AI, a personal fitness and workout coach. "
        "You remember user preferences, workout goals, health details, and personal facts "
        "from previous conversations across sessions and use them to personalize your responses. "
        "You have access to a Firestore database of exercises ('exercises' collection), fitness calculation tools, "
        "real USDA nutrition data via search_food_nutrition, a RAG knowledge base of The Complete Herbal via consult_herbal_knowledge_base, "
        "image generation capabilities via generate_fitness_image (using gemini-3.1-flash-lite-image), "
        "and a secure Agent Platform Python sandbox for running Python code calculations and data analysis. "
        "Use tools like calculate_fitness_metrics for Zone 2 heart rates, search_food_nutrition for macros/calories, "
        "consult_herbal_knowledge_base for herbal remedies, generate_fitness_image to create workout badges and exercise diagrams, "
        "and Python code execution for complex calculations, data transformations, and math."
    ),
    workflow_description="Analyze the user request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


def _get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded project ID."""
    try:
        creds, _ = google.auth.default()
        if creds and not creds.valid:
            creds.refresh(Request())
        return firestore.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        return firestore.Client(project=PROJECT_ID)


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends turn events to Vertex AI Memory Bank for long-term memory extraction."""
    await callback_context.add_session_to_memory()
    return None


def search_exercises(target_muscle: str = "", equipment: str = "", category: str = "") -> str:
    """Searches the exercises collection in Firestore for matching fitness exercises.

    Args:
        target_muscle: Filter by target muscle group (e.g. Chest, Legs, Arms, Back, Abs).
        equipment: Filter by equipment needed (e.g. Dumbbell, Bodyweight, Barbell).
        category: Filter by exercise category (e.g. Strength, Cardio, Core).

    Returns:
        A list of matching exercises with their details and instructions.
    """
    db = _get_firestore_client()
    docs = db.collection("exercises").stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        match = True
        if target_muscle and target_muscle.lower() not in data.get("target_muscle", "").lower():
            match = False
        if equipment and equipment.lower() not in data.get("equipment", "").lower():
            match = False
        if category and category.lower() not in data.get("category", "").lower():
            match = False

        if match:
            results.append(
                f"- {data.get('name')} ({data.get('category')})\n"
                f"  Target Muscle: {data.get('target_muscle')} | Equipment: {data.get('equipment')} | Difficulty: {data.get('difficulty')}\n"
                f"  Instructions: {data.get('instructions')}"
            )

    if not results:
        return "No exercises found matching your criteria in the database."

    return "Found the following exercises:\n" + "\n".join(results)


def get_exercise_details(name: str) -> str:
    """Gets detailed information and instructions for a specific exercise by name from Firestore.

    Args:
        name: Name or partial name of the exercise to look up.

    Returns:
        Detailed exercise information including target muscle, equipment, difficulty, and instructions.
    """
    db = _get_firestore_client()
    docs = db.collection("exercises").stream()

    for doc in docs:
        data = doc.to_dict()
        if name.lower() in data.get("name", "").lower() or doc.id.lower() in name.lower():
            return (
                f"Exercise: {data.get('name')}\n"
                f"Category: {data.get('category')}\n"
                f"Target Muscle: {data.get('target_muscle')}\n"
                f"Equipment: {data.get('equipment')}\n"
                f"Difficulty: {data.get('difficulty')}\n"
                f"Instructions: {data.get('instructions')}"
            )

    return f"No exercise found matching name '{name}'."


def add_exercise(
    name: str,
    category: str,
    target_muscle: str,
    equipment: str,
    difficulty: str,
    instructions: str,
) -> str:
    """Adds a new exercise to the exercises collection in Firestore.

    Args:
        name: Full name of the exercise (e.g. 'Barbell Squat').
        category: Exercise category (e.g. 'Strength', 'Cardio', 'Core').
        target_muscle: Main target muscle group (e.g. 'Legs', 'Chest', 'Back').
        equipment: Equipment required (e.g. 'Barbell', 'Dumbbell', 'Bodyweight').
        difficulty: Difficulty level (e.g. 'Beginner', 'Intermediate', 'Advanced').
        instructions: Step-by-step technique instructions.

    Returns:
        Confirmation message that the exercise was added.
    """
    db = _get_firestore_client()
    doc_id = name.lower().replace(" ", "_").replace("-", "_")
    doc_ref = db.collection("exercises").document(doc_id)

    doc_data = {
        "name": name,
        "category": category,
        "target_muscle": target_muscle,
        "equipment": equipment,
        "difficulty": difficulty,
        "instructions": instructions,
    }

    doc_ref.set(doc_data)
    return f"Successfully added exercise '{name}' to Firestore database (ID: {doc_id})."


def get_weather(query: str) -> str:
    """Simulates a web search for weather information.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def calculate_fitness_metrics(
    age: int,
    resting_hr: int = 60,
    weight_kg: float = 0.0,
    height_cm: float = 0.0,
    gender: str = "male",
    activity_level: str = "moderate",
) -> str:
    """Calculates target heart rate zones (Karvonen formula), BMI, BMR, and TDEE daily energy needs.

    Args:
        age: Age of the user in years.
        resting_hr: Resting heart rate in beats per minute (default: 60 bpm).
        weight_kg: User weight in kilograms (optional, for BMI/BMR/TDEE).
        height_cm: User height in centimeters (optional, for BMI/BMR/TDEE).
        gender: Gender for BMR calculation ('male' or 'female', default: 'male').
        activity_level: Physical activity level ('sedentary', 'light', 'moderate', 'active', 'very_active').

    Returns:
        Formatted summary of heart rate zones, BMI, BMR, and estimated daily energy expenditure (TDEE).
    """
    max_hr = 220 - age
    hrr = max_hr - resting_hr
    z2_low = round(hrr * 0.60 + resting_hr)
    z2_high = round(hrr * 0.70 + resting_hr)
    z4_low = round(hrr * 0.80 + resting_hr)
    z4_high = round(hrr * 0.90 + resting_hr)

    metrics = [
        f"Max Heart Rate: {max_hr} bpm",
        f"Zone 2 Cardio (60-70% intensity): {z2_low} - {z2_high} bpm",
        f"Zone 4 Cardio (80-90% intensity): {z4_low} - {z4_high} bpm",
    ]

    if weight_kg > 0 and height_cm > 0:
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
        if gender.lower() == "female":
            bmr = round(10 * weight_kg + 6.25 * height_cm - 5 * age - 161)
        else:
            bmr = round(10 * weight_kg + 6.25 * height_cm - 5 * age + 5)

        multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9,
        }
        mult = multipliers.get(activity_level.lower(), 1.55)
        tdee = round(bmr * mult)

        metrics.append(f"BMI: {bmi}")
        metrics.append(f"BMR (Basal Metabolic Rate): {bmr} kcal/day")
        metrics.append(f"TDEE (Estimated Daily Energy Need): {tdee} kcal/day")

    return "\n".join(metrics)


def search_food_nutrition(query: str) -> str:
    """Searches USDA FoodData Central public API for real nutrition data (calories, protein, carbs, fats).

    Args:
        query: Food item or ingredient to search (e.g. 'chicken breast', 'protein bar', 'greek yogurt').

    Returns:
        Summary of matching food items with calorie and macro breakdown per serving/100g.
    """
    api_key = os.environ.get("USDA_API_KEY", "DEMO_KEY")
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={encoded_query}&pageSize=4&api_key={api_key}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FitPulseAI/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        foods = data.get("foods", [])
        if not foods:
            return f"No nutritional data found for query '{query}' in USDA database."

        results = []
        for food in foods[:4]:
            desc = food.get("description", "Unknown Food").title()
            nutrients = {
                n.get("nutrientName"): f"{n.get('value')} {n.get('unitName', '').lower()}"
                for n in food.get("foodNutrients", [])
                if n.get("nutrientName")
                in [
                    "Protein",
                    "Energy",
                    "Total lipid (fat)",
                    "Carbohydrate, by difference",
                ]
            }

            cals = nutrients.get("Energy", "N/A")
            protein = nutrients.get("Protein", "N/A")
            carbs = nutrients.get("Carbohydrate, by difference", "N/A")
            fat = nutrients.get("Total lipid (fat)", "N/A")

            results.append(
                f"- {desc}\n"
                f"  Calories: {cals} | Protein: {protein} | Carbs: {carbs} | Fat: {fat}"
            )

        return f"USDA Nutrition Data for '{query}':\n" + "\n".join(results)
    except Exception as e:
        return f"Failed to fetch nutrition data from USDA API: {str(e)}"


RAG_CORPUS_NAME = "projects/1067804430983/locations/us-central1/ragCorpora/150826607051800576"


def consult_herbal_knowledge_base(query: str) -> str:
    """Searches The Complete Herbal RAG corpus for matched passages on herbs, natural remedies, and plants.

    Args:
        query: Herb name, natural remedy, ailment, or plant benefit to search for in the corpus.

    Returns:
        Relevant passages retrieved from The Complete Herbal knowledge base.
    """
    import vertexai
    from vertexai.preview import rag

    try:
        vertexai.init(project=PROJECT_ID, location="us-central1")
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=RAG_CORPUS_NAME)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=4),
        )
    except Exception as e:
        return f"RAG Retrieval failed: {e}"

    contexts = getattr(resp.contexts, "contexts", [])
    passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
    return "\n\n---\n\n".join(passages) or "No relevant passages found in the knowledge base."


async def generate_fitness_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates a visual illustration, workout badge, or exercise form diagram for a fitness item using gemini-3.1-flash-lite-image.

    Args:
        prompt: Description of the fitness visual/image to generate (e.g., 'A modern workout badge for completing 50 squats').

    Returns:
        Public HTTPS URL of the generated image in Cloud Storage.
    """
    import uuid
    from google import genai
    from google.genai.types import GenerateContentConfig, Modality
    from google.cloud import storage

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    try:
        resp = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=GenerateContentConfig(response_modalities=[Modality.TEXT, Modality.IMAGE]),
        )
    except Exception as e:
        return f"Failed to generate image with gemini-3.1-flash-lite-image: {e}"

    image_bytes = None
    if resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                image_bytes = part.inline_data.data
                break

    if not image_bytes:
        return "No image data was returned by the image generation model."

    filename = f"fitness_image_{uuid.uuid4().hex[:8]}.png"

    # (1) Save artifact in Playground's Artifacts panel using tool_context.save_artifact
    if tool_context:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as e:
            print(f"Warning saving artifact: {e}")

    # (2) Upload image bytes directly to public GCS bucket and return public URL
    bucket_name = "fitpulse-ai-assets-qwiklabs-gcp-03-a9a784fdfd5f"
    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob_path = f"generated_images/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type="image/png")
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        return f"Image generated successfully!\nPublic GCS URL: {public_url}"
    except Exception as e:
        return f"Image generated but failed to upload to Cloud Storage: {e}"


async def generate_fitness_video(prompt: str, tool_context: ToolContext) -> str:
    """Generates a short exercise technique demonstration or workout video clip using Google's Omni model (gemini-omni-flash-preview).

    Args:
        prompt: Description of the fitness video to generate (e.g., 'A runner doing sprint drills on a track, smooth motion').

    Returns:
        Public HTTPS URL of the generated MP4 video in Cloud Storage.
    """
    import base64
    import uuid
    from google import genai
    from google.cloud import storage

    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    try:
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )
    except Exception as e:
        return f"Failed to generate video with gemini-omni-flash-preview: {e}"

    video_bytes = None
    if getattr(interaction, "output_video", None) and getattr(interaction.output_video, "data", None):
        data = interaction.output_video.data
        if isinstance(data, str):
            video_bytes = base64.b64decode(data)
        elif isinstance(data, bytes):
            video_bytes = data
    elif hasattr(interaction, "output") and getattr(interaction, "output", None):
        out = interaction.output
        if getattr(out, "data", None):
            video_bytes = base64.b64decode(out.data) if isinstance(out.data, str) else out.data

    if not video_bytes:
        return "No video data was returned by the gemini-omni-flash-preview model."

    filename = f"fitness_video_{uuid.uuid4().hex[:8]}.mp4"

    # (1) Save artifact in Playground's Artifacts panel using tool_context.save_artifact
    if tool_context:
        try:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as e:
            print(f"Warning saving artifact: {e}")

    # (2) Upload video bytes directly to public GCS bucket and return public URL
    bucket_name = "fitpulse-ai-assets-qwiklabs-gcp-03-a9a784fdfd5f"
    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob_path = f"generated_videos/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(video_bytes, content_type="video/mp4")
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        return f"Video generated successfully!\nPublic GCS URL: {public_url}"
    except Exception as e:
        return f"Video generated but failed to upload to Cloud Storage: {e}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=AgentEngineSandboxCodeExecutor(
        agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME
    ),
    tools=[
        PreloadMemoryTool(),
        generate_fitness_video,
        generate_fitness_image,
        consult_herbal_knowledge_base,
        calculate_fitness_metrics,
        search_food_nutrition,
        search_exercises,
        get_exercise_details,
        add_exercise,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
