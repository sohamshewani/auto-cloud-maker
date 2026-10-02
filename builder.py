import os
import json
import time
import random
import subprocess
from pathlib import Path
from groq import Groq

CATEGORIES = [
    {"name": "Everyday Life & Productivity", "desc": "Pantry inventory tracker, recipe scaler, grocery shelf-life monitor, home budget utility."},
    {"name": "Students & Learning", "desc": "Spaced-repetition flashcards, formula cheat-sheet builder, study timer CLI."},
    {"name": "Interactive Terminal Games", "desc": "Text adventure, word puzzle, ASCII dungeon crawler."},
    {"name": "Tools for Professions", "desc": "Compound interest calculator, attendance analyzer, medical dosage unit converter."},
    {"name": "System & Developer Utilities", "desc": "Log rotator, git commit summarizer, API health checker."}
]

LANGUAGES = ["Python", "Shell", "C", "C++", "Java"]

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GH_USER = os.environ.get("GITHUB_ACTOR", "sohamshewani")

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def get_live_model():
    """Dynamically queries Groq API to pick an active text/chat model."""
    try:
        models_data = client.models.list()
        # Find active models that aren't whisper/audio/vision-only
        available = [
            m.id for m in models_data.data 
            if m.active and not any(k in m.id for k in ["whisper", "vision", "guard"])
        ]
        if available:
            print(f"📡 Discovered active Groq models: {available[:3]}")
            return available[0]
    except Exception as e:
        print(f"⚠️ Dynamic discovery failed: {e}")
    # Generic fallback
    return "llama-3.1-8b-instant"

def build_project():
    category = random.choice(CATEGORIES)
    language = random.choice(LANGUAGES)
    active_model = get_live_model()

    print(f"🚀 Designing [{language}] project for [{category['name']}] using [{active_model}]...")

    prompt = f"""
    You are an expert software engineer. Create a complete, lightweight, practical utility project in {language}.
    Inspiration: {category['desc']}
    Return ONLY a single raw valid JSON object with these keys:
    {{
      "repo_name": "short-kebab-case-name",
      "description": "Clear 1-sentence technical description",
      "files": {{
        "relative/path/to/file": "full source code..."
      }},
      "readme": "# Markdown Documentation"
    }}
    Do not wrap output in markdown code blocks.
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=active_model,
        response_format={"type": "json_object"}
    )

    data = json.loads(chat_completion.choices[0].message.content)
    base_name = data.get("repo_name", f"tool-{int(time.time())}")
    description = data.get("description", f"Utility written in {language}")

    work_dir = Path(f"/tmp/{base_name}")
    work_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, code in data.get("files", {}).items():
        dest = work_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        if dest.suffix == ".sh":
            dest.chmod(0o755)

    (work_dir / "README.md").write_text(data.get("readme", f"# {base_name}"), encoding="utf-8")
    (work_dir / ".gitignore").write_text("*.o\n*.class\n__pycache__/\nvenv/\nbuild/\n", encoding="utf-8")

    run("git init", cwd=work_dir)
    run(f"git config user.name '{GH_USER}'", cwd=work_dir)
    run(f"git config user.email '{GH_USER}@users.noreply.github.com'", cwd=work_dir)
    run("git add .", cwd=work_dir)
    run('git commit -m "feat: initial autonomous build"', cwd=work_dir)
    run("git branch -M main", cwd=work_dir)

    name_attempt = base_name
    counter = 1
    while True:
        exists, _, _ = run(f'gh repo view "{GH_USER}/{name_attempt}"')
        if not exists:
            ok, out, err = run(
                f'gh repo create "{name_attempt}" --public --source=. --remote=origin --description "{description}" --push',
                cwd=work_dir
            )
            if ok:
                print(f"✅ Published: https://github.com/{GH_USER}/{name_attempt}")
                break
            counter += 1
            name_attempt = f"{base_name}-v{counter}"
            run("git remote remove origin", cwd=work_dir)
        else:
            counter += 1
            name_attempt = f"{base_name}-v{counter}"

if __name__ == "__main__":
    build_project()
