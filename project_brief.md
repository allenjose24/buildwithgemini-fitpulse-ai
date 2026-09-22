# My agent: FitPulse AI (Fitness & Workout Coach)

One-liner: A conversational agent that helps fitness enthusiasts track workouts, calculate heart rate zones and macro targets, recommend exercise routines from a catalog, and generate motivational progress visuals.

## Tool Coverage
- **Memory**: Remembers user fitness goals, target weight, current fitness level, equipment access, injury history, and preferred exercise types across sessions.
- **Tools**: Looks up exercises by target muscle group/equipment, logs workout sessions, and fetches exercise instructions.
- **Catalog/UI**: Interactive workout routine cards, exercise tables with sets/reps/rest times, and weekly progress summaries (renders via A2UI).
- **Image gen**: Generates exercise form guides, motivational workout milestone badges, and target muscle visualization images.
- **Sandbox**: Computes body composition metrics (BMI, BMR, TDEE), heart rate zones (Karvonen formula), and 1-Rep Max (1RM) calculations.

## Core Rails & Stretch Menu
- **Core rails (everyone)**: Memory (Vertex AI Memory Bank), Function Tools, Eval, Deploy (Agent Platform), Frontend (FastAPI / Cloud Run)
- **My stretch menu (pick later)**: A2UI workout cards, Code Sandbox calculators, Gemini Image Generation
- **First eval question**: "Recommend a 30-minute chest and triceps workout for a beginner with dumbbells only, and calculate my target heart rate for Zone 2 cardio if my age is 30 and resting heart rate is 60 bpm."
