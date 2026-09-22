# FitPulse AI — Personal Workout & Fitness Coach Agent

FitPulse AI is a conversational agent built with the **Google Agent Development Kit (ADK)** and deployed on **Google Cloud Agent Platform**. It helps fitness enthusiasts design personalized exercise routines, compute health and body composition metrics, look up nutrition data, query herbal wellness knowledge, and generate custom workout badges and exercise demonstration videos.

---

## 🎬 Generated Exercise Video Demo

![FitPulse Exercise Demonstration Video](demo_video.webp)

---

## Architecture & Features

### Core Agent Architecture
- **Framework**: Google Agent Development Kit (ADK) v1.1.0 with Python
- **Primary Model**: `gemini-flash-latest` configured with automatic HTTP retry options
- **Protocol**: Agent-to-Agent (A2A) protocol
- **Web Frontend**: Custom FastAPI proxy and lightweight chat UI rendering native A2UI cards

### Integrated Google Cloud Services

- **Vertex AI Memory Bank**
  - Uses `PreloadMemoryTool` and an `after_agent_callback` (`add_session_to_memory`) to extract and recall user fitness goals, target weights, equipment access, and workout preferences across sessions.

- **Google Cloud Firestore**
  - Manages exercise data in the `exercises` Firestore collection via tools for searching (`search_exercises`), inspecting (`get_exercise_details`), and logging new routines (`add_exercise`).

- **Google Cloud Storage (GCS)**
  - Stores generated exercise diagrams, workout milestone badges, and video clips in a public assets bucket (`fitpulse-ai-assets-qwiklabs-gcp-03-a9a784fdfd5f`).

- **Vertex AI RAG Engine**
  - Performs retrieval-augmented generation (`consult_herbal_knowledge_base`) against a serverless RAG corpus of *The Complete Herbal* to answer botanical and traditional wellness queries.

- **Agent Platform Code Execution Sandbox**
  - Configured with `AgentEngineSandboxCodeExecutor` to safely execute Python code for calculating body composition metrics (BMI, BMR, TDEE) and Karvonen heart rate zones (`calculate_fitness_metrics`).

- **Gemini Image & Video Generation**
  - **Image Generation**: Uses `gemini-3.1-flash-lite-image` (`generate_fitness_image`) to create workout milestone badges and exercise form diagrams.
  - **Video Generation**: Uses `gemini-omni-flash-preview` (`generate_fitness_video`) in the global region to generate exercise demonstration video clips.

- **A2UI (Agent-to-User Interface) v0.8**
  - Formats agent responses into rich display surfaces (Cards, Columns, Rows, Text, Images) rendered natively in the ADK Web UI and the custom web frontend.

- **USDA FoodData Central API**
  - Fetches real-time nutritional profiles, calorie counts, and macronutrient breakdowns (`search_food_nutrition`).

---

## Repository Structure

```
.
├── app/
│   ├── agent.py            # Main ADK root_agent, tools, callbacks, and A2UI system prompt
│   ├── a2ui_utils.py       # A2UI response formatting callback wrapper
│   └── fast_api_app.py     # FastAPI application wrapper for ADK
├── frontend/
│   ├── main.py             # FastAPI proxy connecting browser to deployed Agent Platform runtime
│   ├── static/
│   │   └── index.html      # Rebranded dark-mode chat UI with A2UI mini-renderer
│   └── Dockerfile          # Container specification for Cloud Run deployment
├── project_brief.md        # Initial project specification
└── agents-cli-manifest.yaml# Agent manifest configuration
```

---

## Local Development & Setup

### Prerequisites
- Python 3.11+
- Google Cloud SDK (`gcloud`) authenticated with Application Default Credentials
- Access to a Google Cloud project with Vertex AI and Firestore APIs enabled

### 1. Set Up Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
```

### 2. Run the Agent Locally in ADK Web UI
```bash
adk web app
```
The ADK Web UI will start on port 8080.

### 3. Run the Custom FastAPI Frontend Locally
```bash
cd frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
python main.py
```

---

## Deployment Instructions

### Deploy Agent to Agent Platform
```bash
agents-cli deploy --no-confirm-project
```

### Deploy Frontend to Cloud Run
```bash
cd frontend
gcloud run deploy fitpulse-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>",AGENT_DIRECTORY="app"
```

### Grant Cloud Run IAM Permissions
Grant the Cloud Run service account access to invoke the Agent Platform runtime:
```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```
