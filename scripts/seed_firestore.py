"""Seed Firestore collections for FitCoach AI."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-127b16e62fe4"

WORKOUT_ROUTINES = [
    {
        "id": "hiit-full-body",
        "name": "Full Body HIIT Blast",
        "category": "HIIT",
        "difficulty": "Intermediate",
        "duration_minutes": 30,
        "target_muscle_groups": ["Full Body", "Core", "Quads"],
        "equipment_needed": ["Kettlebell", "Jump Rope"],
        "description": "High-intensity interval training focusing on full-body explosive power and core strength.",
    },
    {
        "id": "strength-hypertrophy-push",
        "name": "Upper Body Push Strength",
        "category": "Strength",
        "difficulty": "Advanced",
        "duration_minutes": 45,
        "target_muscle_groups": ["Chest", "Shoulders", "Triceps"],
        "equipment_needed": ["Dumbbells", "Bench"],
        "description": "Hypertrophy-focused upper body push workout for building chest and shoulder muscle mass.",
    },
    {
        "id": "mobility-flexibility-recovery",
        "name": "Active Recovery & Mobility Flow",
        "category": "Mobility",
        "difficulty": "Beginner",
        "duration_minutes": 20,
        "target_muscle_groups": ["Hips", "Hamstrings", "Thoracic Spine"],
        "equipment_needed": ["Yoga Mat", "Foam Roller"],
        "description": "Gentle mobility and foam rolling routine designed for active recovery and injury prevention.",
    },
]

FITNESS_GEAR = [
    {
        "id": "gear-adjustable-dumbbells",
        "name": "ProFlex Adjustable Dumbbells 5-50lbs",
        "category": "Strength",
        "price": 299.99,
        "description": "Space-saving adjustable dumbbell set with rapid weight selector dials.",
        "best_for": "Home gym strength training",
    },
    {
        "id": "gear-foam-roller-grid",
        "name": "TriggerPoint GRID Foam Roller",
        "category": "Recovery",
        "price": 39.99,
        "description": "Multi-density foam roller designed to relieve muscle tightness and enhance recovery.",
        "best_for": "Myofascial release and post-workout recovery",
    },
    {
        "id": "gear-smart-hr-strap",
        "name": "PulseBeat Pro Heart Rate Monitor",
        "category": "Electronics",
        "price": 79.99,
        "description": "Chest-strap ECG heart rate sensor with Bluetooth and ANT+ connectivity.",
        "best_for": "Accurate heart-rate zone tracking",
    },
]


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)

    # Seed workout_routines
    routines_ref = db.collection("workout_routines")
    for routine in WORKOUT_ROUTINES:
        doc_id = routine["id"]
        routines_ref.document(doc_id).set(routine)
        print(f"Seeded workout routine: {routine['name']} ({doc_id})")

    # Seed fitness_gear
    gear_ref = db.collection("fitness_gear")
    for gear in FITNESS_GEAR:
        doc_id = gear["id"]
        gear_ref.document(doc_id).set(gear)
        print(f"Seeded fitness gear: {gear['name']} ({doc_id})")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed_database()
