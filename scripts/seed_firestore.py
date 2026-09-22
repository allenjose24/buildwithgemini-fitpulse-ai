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

"""Seed script for populating the exercises collection in Firestore."""

import google.auth
from google.auth.transport.requests import Request
from google.cloud import firestore

# Hardcoded Project ID string (do NOT use google.auth.default or env vars for project ID)
PROJECT_ID = "qwiklabs-gcp-03-a9a784fdfd5f"

SEED_EXERCISES = [
    {
        "id": "pushup",
        "name": "Push-up",
        "category": "Strength",
        "target_muscle": "Chest",
        "equipment": "Bodyweight",
        "difficulty": "Beginner",
        "instructions": "Place hands shoulder-width apart, lower chest to floor, push back up keeping core tight.",
    },
    {
        "id": "dumbbell_bench_press",
        "name": "Dumbbell Bench Press",
        "category": "Strength",
        "target_muscle": "Chest",
        "equipment": "Dumbbell",
        "difficulty": "Intermediate",
        "instructions": "Lie flat on a bench holding dumbbells at chest height, press weights upward until arms extend, lower under control.",
    },
    {
        "id": "goblet_squat",
        "name": "Goblet Squat",
        "category": "Strength",
        "target_muscle": "Legs",
        "equipment": "Dumbbell",
        "difficulty": "Beginner",
        "instructions": "Hold a dumbbell vertically at chest level, squat down until thighs are parallel to the ground, drive through heels to stand.",
    },
    {
        "id": "plank",
        "name": "Forearm Plank",
        "category": "Core",
        "target_muscle": "Abs",
        "equipment": "Bodyweight",
        "difficulty": "Beginner",
        "instructions": "Hold a forearm plank position with elbows under shoulders, maintaining a straight line from head to heels.",
    },
    {
        "id": "dumbbell_row",
        "name": "Single-Arm Dumbbell Row",
        "category": "Strength",
        "target_muscle": "Back",
        "equipment": "Dumbbell",
        "difficulty": "Intermediate",
        "instructions": "Support one knee and hand on a bench, pull dumbbell up to your hip with the opposite arm, squeeze upper back.",
    },
    {
        "id": "bicep_curl",
        "name": "Dumbbell Bicep Curl",
        "category": "Strength",
        "target_muscle": "Arms",
        "equipment": "Dumbbell",
        "difficulty": "Beginner",
        "instructions": "Stand shoulder-width apart holding dumbbells at sides, curl weights toward shoulders while keeping elbows stationary.",
    },
]


def seed_database():
    """Seeds the exercises collection in Firestore."""
    creds, _ = google.auth.default()
    if creds and not creds.valid:
        try:
            creds.refresh(Request())
        except Exception:
            pass

    db = firestore.Client(project=PROJECT_ID, credentials=creds)
    collection_ref = db.collection("exercises")

    print(f"Seeding Firestore collection 'exercises' in project '{PROJECT_ID}'...")
    for item in SEED_EXERCISES:
        doc_id = item["id"]
        doc_data = {k: v for k, v in item.items() if k != "id"}
        collection_ref.document(doc_id).set(doc_data)
        print(f"  ✓ Added exercise: {item['name']} ({doc_id})")

    print("\nFirestore seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
