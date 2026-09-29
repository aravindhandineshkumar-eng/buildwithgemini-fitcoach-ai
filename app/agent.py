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
from typing import Optional

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback



PROJECT_ID = "qwiklabs-gcp-03-127b16e62fe4"
BUCKET_NAME = "fitcoach-ai-media-qwiklabs-gcp-03-127b16e62fe4"


def _get_code_executor():
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
                sandbox_name = meta.get("sandbox_resource_name")
                agent_engine_name = meta.get("remote_agent_runtime_id")
                if sandbox_name:
                    return AgentEngineSandboxCodeExecutor(sandbox_resource_name=sandbox_name)
                elif agent_engine_name:
                    return AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_name)
        except Exception:
            pass
    return AgentEngineSandboxCodeExecutor()




def _get_db():
    return firestore.Client(project=PROJECT_ID)


def search_workout_routines(category: str = "") -> str:
    """Search or list workout routines stored in the Firestore database.

    Args:
        category: Optional category filter (e.g. 'HIIT', 'Strength', 'Mobility'). Pass empty string to list all.

    Returns:
        A list of matching workout routines with their details.
    """
    db = _get_db()
    routines_ref = db.collection("workout_routines")
    docs = routines_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if category:
            doc_category = str(data.get("category", "")).lower()
            if category.lower() not in doc_category:
                continue
        results.append(data)

    if not results:
        return f"No workout routines found matching category '{category}'."

    output = ["Found workout routines:"]
    for item in results:
        output.append(
            f"- [{item.get('id')}] {item.get('title')} ({item.get('category')}, {item.get('difficulty')} level, {item.get('duration_minutes')} min)\n"
            f"  Target: {', '.join(item.get('target_muscle_groups', [])) if isinstance(item.get('target_muscle_groups'), list) else item.get('target_muscle_groups')}\n"
            f"  Exercises: {', '.join(item.get('exercises', [])) if isinstance(item.get('exercises'), list) else item.get('exercises')}"
        )
    return "\n".join(output)


def get_workout_routine(routine_id: str) -> str:
    """Retrieve details for a specific workout routine by ID from Firestore.

    Args:
        routine_id: The document ID of the workout routine (e.g. 'hiit-full-body').

    Returns:
        The full detail of the requested routine.
    """
    db = _get_db()
    doc_ref = db.collection("workout_routines").document(routine_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Workout routine with ID '{routine_id}' was not found in Firestore."
    
    data = doc.to_dict()
    return f"Routine Details [{routine_id}]:\nTitle: {data.get('title')}\nCategory: {data.get('category')}\nDifficulty: {data.get('difficulty')}\nDuration: {data.get('duration_minutes')} mins\nTarget Muscles: {data.get('target_muscle_groups')}\nExercises: {data.get('exercises')}"


def add_workout_routine(
    routine_id: str,
    title: str,
    category: str,
    difficulty: str,
    duration_minutes: int,
    target_muscle_groups: str,
    exercises_description: str,
) -> str:
    """Add or save a new workout routine document to the Firestore database.

    Args:
        routine_id: Unique ID for the routine slug (e.g. 'core-burner-15').
        title: Descriptive title of the workout.
        category: Category such as 'HIIT', 'Strength', 'Cardio', 'Mobility'.
        difficulty: 'Beginner', 'Intermediate', or 'Advanced'.
        duration_minutes: Total duration in minutes.
        target_muscle_groups: Comma-separated target muscles (e.g. 'Abs, Core, Lower Back').
        exercises_description: Comma-separated list or description of exercises included.

    Returns:
        Confirmation message.
    """
    db = _get_db()
    muscles = [m.strip() for m in target_muscle_groups.split(",") if m.strip()]
    ex_list = [e.strip() for e in exercises_description.split(",") if e.strip()]

    doc_ref = db.collection("workout_routines").document(routine_id)
    doc_ref.set({
        "title": title,
        "category": category,
        "difficulty": difficulty,
        "duration_minutes": duration_minutes,
        "target_muscle_groups": muscles,
        "exercises": ex_list,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    return f"Successfully saved workout routine '{title}' with ID '{routine_id}' to Firestore!"


def search_fitness_gear(category: str = "") -> str:
    """Search or list fitness equipment and athletic gear from Firestore.

    Args:
        category: Optional category filter (e.g. 'Weights', 'Recovery', 'Wearables'). Pass empty string for all.

    Returns:
        List of matching fitness gear items.
    """
    db = _get_db()
    gear_ref = db.collection("fitness_gear")
    docs = gear_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        if category:
            if category.lower() not in str(data.get("category", "")).lower():
                continue
        results.append(data)

    if not results:
        return f"No fitness gear found matching category '{category}'."

    output = ["Found fitness gear:"]
    for item in results:
        output.append(
            f"- [{item.get('id')}] {item.get('name')} (${item.get('price_usd')} USD)\n"
            f"  Category: {item.get('category')} | Target: {item.get('target_activity')}\n"
            f"  Description: {item.get('description')}"
        )
    return "\n".join(output)


def add_fitness_gear(
    gear_id: str,
    name: str,
    category: str,
    price_usd: float,
    description: str,
    target_activity: str,
) -> str:
    """Add a new fitness equipment item to the Firestore database.

    Args:
        gear_id: Unique slug for the item (e.g. 'kettlebell-24kg').
        name: Full product name.
        category: Category (e.g. 'Weights', 'Cardio', 'Wearables').
        price_usd: Price in USD.
        description: Feature details and recommendations.
        target_activity: Intended activity or sport.

    Returns:
        Confirmation message.
    """
    db = _get_db()
    doc_ref = db.collection("fitness_gear").document(gear_id)
    doc_ref.set({
        "name": name,
        "category": category,
        "price_usd": price_usd,
        "description": description,
        "target_activity": target_activity,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    return f"Successfully saved fitness gear '{name}' with ID '{gear_id}' to Firestore!"


def calculate_heart_rate_zones(age: int, resting_hr: int = 60) -> str:
    """Calculate training heart rate zones using the Karvonen method based on age and resting heart rate.

    Args:
        age: User's age in years.
        resting_hr: Resting heart rate in beats per minute (default 60 bpm).

    Returns:
        Breakdown of target heart rate zones (BPM ranges).
    """
    max_hr = 220 - age
    hrr = max_hr - resting_hr

    def zone_range(low_pct, high_pct):
        low = round(resting_hr + (hrr * low_pct))
        high = round(resting_hr + (hrr * high_pct))
        return f"{low}-{high} BPM"

    return (
        f"Heart Rate Training Zones for Age {age} (Resting HR: {resting_hr} BPM):\n"
        f"- Max Heart Rate: {max_hr} BPM\n"
        f"- Zone 1 (Warm-up 50-60%): {zone_range(0.50, 0.60)}\n"
        f"- Zone 2 (Fat Burn 60-70%): {zone_range(0.60, 0.70)}\n"
        f"- Zone 3 (Aerobic 70-80%): {zone_range(0.70, 0.80)}\n"
        f"- Zone 4 (Anaerobic 80-90%): {zone_range(0.80, 0.90)}\n"
        f"- Zone 5 (Peak 90-100%): {zone_range(0.90, 1.00)}"
    )


def search_public_exercise_db(category: str = "") -> str:
    """Fetch real exercise data from the wger Open Exercise Database public API.

    Args:
        category: Optional category filter (e.g. 'Abs', 'Legs', 'Arms', 'Chest', 'Shoulders').

    Returns:
        Summary of exercises from the public database.
    """
    api_key = os.environ.get("WGER_API_KEY", "")
    url = "https://wger.de/api/v2/exerciseinfo/?limit=20"
    headers = {"User-Agent": "FitCoachAI/1.0"}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            results = data.get("results", [])
            exercises = []
            for item in results:
                cat_name = item.get("category", {}).get("name", "General")
                if category and category.lower() not in cat_name.lower():
                    continue
                trans = item.get("translations", [])
                name = ""
                for t in trans:
                    if t.get("language") == 2:  # 2 = English
                        name = t.get("name", "")
                        break
                if not name and trans:
                    name = trans[0].get("name", "Exercise")
                if name:
                    exercises.append(f"- [{cat_name}] {name}")
                if len(exercises) >= 7:
                    break
            if not exercises:
                return f"No exercises found in public database for category '{category}'."
            return "Exercises from wger Open Exercise Database:\n" + "\n".join(exercises)
    except Exception as e:
        return f"Error fetching from public exercise API: {str(e)}"


def geocode_address(address: str) -> str:
    """Convert an address or location name into geographic coordinates (latitude and longitude) using the Geocoding API.

    Args:
        address: Full address or location query (e.g. '1600 Amphitheatre Parkway, Mountain View, CA').

    Returns:
        Formatted location details with name, formatted address, and coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                res = data["results"][0]
                fmt_address = res.get("formatted_address", address)
                loc = res.get("geometry", {}).get("location", {})
                lat = loc.get("lat")
                lng = loc.get("lng")
                return f"Geocoded Address:\n- Query: {address}\n- Formatted Address: {fmt_address}\n- Location: ({lat}, {lng})"
            return f"Geocoding API failed with status: {data.get('status')} for query '{address}'."
    except Exception as e:
        return f"Error calling Geocoding API: {str(e)}"


def find_nearby_places(place_type: str, latitude: float, longitude: float, radius_meters: float = 5000.0) -> str:
    """Find nearby places of a given type around a location using Places API (New).

    Args:
        place_type: Type of place to search for (e.g. 'gym', 'park', 'sports_complex', 'fitness_center').
        latitude: Latitude of center location.
        longitude: Longitude of center location.
        radius_meters: Search radius in meters (default 5000 meters / 5km).

    Returns:
        Formatted summary of nearby places with name, address, and coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            places = data.get("places", [])
            if not places:
                return f"No nearby '{place_type}' places found within {radius_meters}m of ({latitude}, {longitude})."

            results = []
            for p in places[:10]:
                name = p.get("displayName", {}).get("text", "Unknown Place")
                address = p.get("formattedAddress", "N/A")
                loc = p.get("location", {})
                lat = loc.get("latitude")
                lng = loc.get("longitude")
                results.append(f"- Name: {name}\n  Address: {address}\n  Location: ({lat}, {lng})")

            return f"Found {len(results)} nearby '{place_type}' places:\n" + "\n".join(results)
    except Exception as e:
        return f"Error calling Places API (New): {str(e)}"


def generate_workout_gear_image(prompt: str, tool_context: ToolContext) -> str:
    """Generate an image for fitness gear, equipment, or workout motivation using gemini-3.1-flash-lite-image in the global region.

    Args:
        prompt: Detailed description of the fitness image to generate (e.g. 'A sleek modern sports water bottle').
        tool_context: ADK ToolContext for saving the artifact.

    Returns:
        Public HTTPS URL of the generated image.
    """
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="global",
    )
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
    )

    img_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                img_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not img_bytes:
        return "Failed to generate image bytes from gemini-3.1-flash-lite-image model."

    # (1) Save with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    filename = f"fitness_image_{int(datetime.datetime.now().timestamp())}.jpg"
    artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # (2) Upload image bytes to public Cloud Storage bucket and return public HTTPS URL
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(img_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return f"Successfully generated and uploaded image!\nPublic URL: {public_url}"


def get_weather(query: str) -> str:
    """Simulates getting weather information.

    Args:
        query: Location string.

    Returns:
        Simulated weather information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting current time.

    Args:
        query: City name.

    Returns:
        Current time string.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: Send the session events to Memory Bank for cross-session memory extraction."""
    try:
        await callback_context.add_session_to_memory()
    except ValueError:
        pass
    return None



def memory_bank_service_builder():
    """Build memory service pointing to the Vertex AI Memory Bank for deployment."""
    engine_id = "3696133681094590464"
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
                remote_id = meta.get("remote_agent_runtime_id")
                if remote_id:
                    engine_id = remote_id.split("/")[-1]
        except Exception:
            pass
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=engine_id,
    )



_a2ui_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = _a2ui_manager.generate_system_prompt(
    role_description=(
        "You are FitCoach AI, an intelligent Workout & Gear Coach. "
        "You help users look up workout routines, recommend athletic gear, track fitness preferences across sessions, "
        "calculate heart-rate training zones, geocode addresses, find nearby gyms, generate workout/gear images using gemini-3.1-flash-lite-image, search the public wger exercise database, execute Python code safely in a sandbox, and save new workout routines or gear items to your Firestore database."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
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


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=_get_code_executor(),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        search_workout_routines,
        get_workout_routine,
        add_workout_routine,
        search_fitness_gear,
        add_fitness_gear,
        calculate_heart_rate_zones,
        search_public_exercise_db,
        geocode_address,
        find_nearby_places,
        generate_workout_gear_image,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)






