import os
import urllib.request

REPO = "Samarth-Goyal-1401/OpenEnv_Meta_AI_Hackathon_Project"
BRANCH = "dev2/graders-baseline"
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

FILES = [
    "context_router/graders/__init__.py",
    "context_router/graders/grader_easy.py",
    "context_router/graders/grader_medium.py",
    "context_router/graders/grader_hard.py",
    "context_router/tasks/__init__.py",
    "context_router/tasks/task_definitions.py",
    "context_router/tests/__init__.py",
    "context_router/tests/test_grader_easy.py",
    "context_router/tests/test_grader_medium.py",
    "context_router/tests/test_grader_hard.py",
    "context_router/server/app.py",
    "context_router/server/context_env.py",
    "context_router/client.py",
    "context_router/models.py",
]

DEST_DIR = r"d:\OpenENV\dev2_staging"

def sync_files():
    for f in FILES:
        url = f"{BASE_URL}/{f}"
        dest_path = os.path.join(DEST_DIR, f)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            print(f"Downloading {f}...")
            urllib.request.urlretrieve(url, dest_path)
        except Exception as e:
            print(f"Failed to download {f}: {e}")

if __name__ == "__main__":
    sync_files()
    print("Sync complete.")
