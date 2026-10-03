import os
import json
import time
import random
import re
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

LANGUAGES = ["C++", "C", "Java", "Python", "Shell"]

DOMAIN_CHALLENGES = [
    {
        "domain": "Storage Engines & Distributed Infrastructure",
        "challenges": [
            "Log-Structured Merge-tree (LSM) key-value engine with write-ahead logging (WAL), Bloom filter pruning, and leveled compaction",
            "Distributed consensus Raft protocol state machine implementation with leader election, log compaction, and RPC heartbeats",
            "Zero-copy userspace packet filter using ring buffers, sliding-window flow control, and memory arena pooling",
            "Async epoll and kqueue high-concurrency event-driven network server with connection pooling and non-blocking I/O"
        ]
    },
    {
        "domain": "Systems, Compilers & Runtimes",
        "challenges": [
            "Recursive-descent AST parser and bytecode virtual machine interpreter for a custom typed expression language",
            "Static analysis dead-code and memory leak detector using control-flow graph (CFG) graph traversal",
            "In-memory columnar database storage engine with vectorized scan operations, dictionary encoding, and bitmap indices"
        ]
    },
    {
        "domain": "Everyday Life & Professional Algorithms",
        "challenges": [
            "Adaptive spaced-repetition Leitner algorithmic engine with forgetting-curve analytics and Markdown flashcard export",
            "Pediatric and ICU clinical drug dosage titration calculator with cross-interaction safety validation engines",
            "High-throughput concurrent rate limiter using token bucket and distributed sliding-window counters"
        ]
    }
]

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
GH_USER = os.environ.get("GITHUB_ACTOR", "sohamshewani")
MODEL_NAME = "gemini-3.8-flash"


def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def ask_gemini(prompt: str, json_mode: bool = False, max_tokens: int = 5000) -> str:
    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=0.2
    )
    if json_mode:
        config.response_mime_type = "application/json"

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            print(f"⚠️ Gemini request retry ({attempt + 1}/3): {e}")
            time.sleep(5)
    raise RuntimeError("Gemini API generation failed.")

def execute_deep_build():
    category = random.choice(DOMAIN_CHALLENGES)
    topic = random.choice(category["challenges"])
    language = random.choice(LANGUAGES)

    print("=" * 70)
    print(f"🚀 INITIATING DEEP CLOUD PIPELINE VIA GEMINI 2.5 FLASH: [{language}]")
    print(f"🎯 Domain: {category['domain']}")
    print(f"🎯 Objective: {topic}")
    print("=" * 70)

    # Stage 1: Architecture Specification & Manifest
    print("\n[Stage 1/4: Systems Research] 🔬 Generating architecture specification...")
    spec_prompt = f"""
    You are a Principal Systems Architect. Design an enterprise-grade, production-quality system in {language} for: '{topic}'.
    Demand senior-level engineering rigor: clean separation of concerns, modular directory hierarchy (src/, include/, tests/), 
    and complete defensive programming.
    Return ONLY a single valid JSON object:
    {{
      "repo_name": "kebab-case-project-name",
      "description": "Professional 1-sentence technical GitHub summary mentioning {language}",
      "architecture_summary": "Exhaustive technical description of data structures, concurrency model, and data flow",
      "files": {{
        "relative/path/to/file": "full complete compilable code..."
      }},
      "readme": "# Markdown Documentation"
    }}
    CRITICAL: Write COMPLETE, UNTRUNCATED, compilable source files. Include build automation (Makefile, pom.xml, or requirements.txt), 
    modular core engines, comprehensive unit/integration test suites, and an exhaustive README with ASCII architecture diagrams.
    """

    raw_output = ask_gemini(spec_prompt, json_mode=True, max_tokens=8000)
    data = json.loads(raw_output)

    base_name = data.get("repo_name", f"{language.lower()}-engine-{int(time.time())}")
    description = data.get("description", f"Enterprise {language} systems engine")
    work_dir = Path(f"/tmp/{base_name}")
    work_dir.mkdir(parents=True, exist_ok=True)

    # Stage 2 & 3: File Deployment
    print(f"\n[Stage 2 & 3: Implementation & Harness] 📦 Writing complete file tree for {base_name}...")
    for rel_path, code in data.get("files", {}).items():
        dest = work_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        if dest.suffix in [".sh", ".py"]:
            dest.chmod(0o755)

    (work_dir / "README.md").write_text(data.get("readme", f"# {base_name}"), encoding="utf-8")
    (work_dir / ".gitignore").write_text("*.o\n*.a\n*.out\n*.class\ntarget/\nbuild/\nbin/\nvenv/\n__pycache__/\n.DS_Store\n", encoding="utf-8")

    # Native CI/CD Workflow
    ci_path = work_dir / ".github" / "workflows" / "ci.yml"
    ci_path.parent.mkdir(parents=True, exist_ok=True)
    ci_path.write_text(
        "name: CI\non: [push, pull_request]\njobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: Verify Tree\n        run: ls -laR\n",
        encoding="utf-8"
    )

    # Stage 4: Cloud Publishing
    print("\n[Stage 4/4: Cloud Publishing] 🚀 Pushing production repository to GitHub...")
    run("git init", cwd=work_dir)
    run(f"git config user.name '{GH_USER}'", cwd=work_dir)
    run(f"git config user.email '{GH_USER}@users.noreply.github.com'", cwd=work_dir)
    run("git add .", cwd=work_dir)
    run('git commit -m "feat: complete production architecture with tests and ci"', cwd=work_dir)
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
                print(f"\n🌟 Published Production Repository: https://github.com/{GH_USER}/{name_attempt}")
                break
            counter += 1
            name_attempt = f"{base_name}-v{counter}"
            run("git remote remove origin", cwd=work_dir)
        else:
            counter += 1
            name_attempt = f"{base_name}-v{counter}"

if __name__ == "__main__":
    execute_deep_build()
