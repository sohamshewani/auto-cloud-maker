import os
import json
import time
import random
import re
import subprocess
from pathlib import Path
from groq import Groq

LANGUAGES = ["Java", "C++", "C", "Python", "Shell"]

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

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GH_USER = os.environ.get("GITHUB_ACTOR", "sohamshewani")

# Priority fallback sequence: High intelligence first, high TPM backup second
MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def ask_groq(prompt: str, json_mode: bool = True, max_tokens: int = 1800) -> str:
    """Robust API invoker with exponential backoff and automatic model fallback."""
    for model in MODELS:
        for attempt in range(5):
            try:
                kwargs = {
                    "messages": [{"role": "user", "content": prompt}],
                    "model": model,
                    "max_tokens": max_tokens
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                
                res = client.chat.completions.create(**kwargs)
                return res.choices[0].message.content
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    # Look for recommended retry interval, default to exponential backoff
                    wait_match = re.search(r"try again in ([\d\.]+)s", err_str)
                    sleep_time = float(wait_match.group(1)) + 2.0 if wait_match else (15 * (attempt + 1))
                    print(f"⏳ Rate limit on [{model}]. Backing off {sleep_time:.1f}s (attempt {attempt+1}/5)...")
                    time.sleep(sleep_time)
                else:
                    print(f"⚠️ Error with [{model}]: {e}. Switching fallback model...")
                    break
    raise RuntimeError("All LLM endpoints and retries exhausted.")

def stage_1_systems_research(topic: str, language: str) -> dict:
    print(f"\n[Stage 1/4: Systems Research] 🔬 Specifying architecture for: '{topic}' ({language})...")
    prompt = f"""
    You are a Principal Software Architect. Design a production-grade, deep engineering system in {language} for: '{topic}'.
    Demand high rigor: modular packages, zero toy shortcuts, clear separation of concerns, and clean interfaces.
    Return ONLY a valid JSON object:
    {{
      "repo_name": "kebab-case-system-name",
      "description": "Professional technical 1-sentence GitHub summary mentioning {language}",
      "architecture_summary": "Deep architectural explanation of data flow, memory model, and concurrency",
      "file_manifest": ["src/...", "include/...", "Makefile or pom.xml or requirements.txt"]
    }}
    Do not output markdown backticks outside JSON.
    """
    return json.loads(ask_groq(prompt, json_mode=True, max_tokens=1000))

def stage_2_core_implementation(spec: dict, language: str) -> dict:
    print(f"[Stage 2/4: Core Implementation] ⚙️️ Building core modules and libraries...")
    # Buffer between API stages to keep tokens-per-minute low
    time.sleep(5)
    prompt = f"""
    You are the Lead Systems Engineer. Implement the core modules for '{spec['repo_name']}' in {language}.
    Spec: {spec['architecture_summary']}
    Required files: {spec['file_manifest']}
    Write real, production-quality implementation files. Provide clean separation of concerns and robust error handling.
    Return ONLY a single valid JSON dictionary where keys are relative file paths and values are complete code strings:
    {{
      "relative/path/to/file": "complete code..."
    }}
    Do not output markdown code blocks outside JSON.
    """
    return json.loads(ask_groq(prompt, json_mode=True, max_tokens=2200))

def stage_3_verification_and_harness(spec: dict, core_files: dict, language: str) -> dict:
    print(f"[Stage 3/4: Verification & Harness] 🧪 Engineering integration tests and build automation...")
    time.sleep(5)
    prompt = f"""
    You are a Staff QA & DevOps Engineer for '{spec['repo_name']}' in {language}.
    Existing modules: {list(core_files.keys())}
    Generate all build automation (Makefile, pom.xml, CMakeLists.txt, or requirements.txt), test runners, 
    and comprehensive unit/edge-case tests.
    Return ONLY a single valid JSON dictionary of additional file paths to complete code strings:
    {{
      "tests/test_...": "test suite code...",
      "Makefile": "build rules..."
    }}
    Do not output markdown code blocks outside JSON.
    """
    return json.loads(ask_groq(prompt, json_mode=True, max_tokens=1800))

def stage_4_enterprise_documentation(spec: dict, all_files: list, language: str) -> str:
    print(f"[Stage 4/4: Documentation] 📚 Publishing exhaustive architecture specification & docs...")
    time.sleep(5)
    repo_name = spec['repo_name']
    prompt = f"""
    Write an exhaustive, enterprise-grade README.md for '{repo_name}' in {language}.
    Files included: {all_files}
    Structure:
    - Badges (use https://img.shields.io/badge/License-MIT-yellow.svg and https://img.shields.io/github/stars/{GH_USER}/{repo_name}?style=flat)
    - Architecture & Problem Statement
    - ASCII Architecture / Dataflow Diagram
    - Algorithmic Decisions & Concurrency Invariants
    - Build, Compilation & Test Execution Recipes
    Output ONLY raw Markdown.
    """
    return ask_groq(prompt, json_mode=False, max_tokens=2000)

def execute_deep_build():
    category = random.choice(DOMAIN_CHALLENGES)
    topic = random.choice(category["challenges"])
    language = random.choice(LANGUAGES)

    print("=" * 70)
    print(f"🚀 INITIATING DEEP CLOUD ENGINEERING CYCLE: [{language}]")
    print(f"🎯 Domain: {category['domain']}")
    print(f"🎯 Objective: {topic}")
    print("=" * 70)

    spec = stage_1_systems_research(topic, language)
    core_files = stage_2_core_implementation(spec, language)
    harness_files = stage_3_verification_and_harness(spec, core_files, language)

    all_files = {**core_files, **harness_files}
    readme_content = stage_4_enterprise_documentation(spec, list(all_files.keys()), language)

    base_name = spec.get("repo_name", f"{language.lower()}-engine-{int(time.time())}")
    description = spec.get("description", f"Enterprise {language} systems engine")
    work_dir = Path(f"/tmp/{base_name}")
    work_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, code in all_files.items():
        dest = work_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        if dest.suffix in [".sh", ".py"]:
            dest.chmod(0o755)

    (work_dir / "README.md").write_text(readme_content, encoding="utf-8")
    (work_dir / ".gitignore").write_text("*.o\n*.a\n*.out\n*.class\ntarget/\nbuild/\nbin/\nvenv/\n__pycache__/\n.DS_Store\n", encoding="utf-8")

    # Native CI automation workflow
    ci_path = work_dir / ".github" / "workflows" / "ci.yml"
    ci_path.parent.mkdir(parents=True, exist_ok=True)
    ci_path.write_text(
        "name: CI\non: [push, pull_request]\njobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - name: Verify Tree\n        run: ls -laR\n",
        encoding="utf-8"
    )

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
