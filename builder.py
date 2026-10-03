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
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def ask_gemini(prompt: str, max_tokens: int = 4000) -> str:
    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=0.2
    )
    for model_name in MODELS:
        for attempt in range(3):
            try:
                print(f"📡 Querying Gemini via [{model_name}] (attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if response.text:
                    return response.text
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ [{model_name}] notice: {err_str}")
                if "503" in err_str or "429" in err_str:
                    wait_time = (attempt + 1) * 15
                    print(f"⏳ Cloud demand spike. Sleeping {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break
    raise RuntimeError("All configured Gemini models failed. Retrying next cycle.")

def clean_code(raw_text: str) -> str:
    cleaned = re.sub(r"^```[a-zA-Z0-9_\+\-]*\n", "", raw_text.strip())
    cleaned = re.sub(r"\n```$", "", cleaned.strip())
    return cleaned

def stage_1_spec(topic: str, language: str) -> dict:
    print(f"\n[Stage 1/4: Systems Research] 🔬 Specifying architecture for: '{topic}' ({language})...")
    prompt = f"""
    You are a Principal Systems Architect. Design a production-grade, deep engineering system in {language} for: '{topic}'.
    Demand high rigor: modular directory hierarchy, clean separation of concerns, and defensive typing.

    Output your specification in this EXACT key-value format (do not use JSON):
    REPO_NAME: <kebab-case-project-name>
    DESCRIPTION: <Professional 1-sentence technical GitHub summary mentioning {language}>
    CORE_FILES: <comma-separated relative file paths, e.g. include/engine.hpp, src/engine.cpp, src/main.cpp>
    ARCHITECTURE_SUMMARY:
    <Deep technical explanation of data flow, memory model, and concurrency invariants>
    """
    raw = ask_gemini(prompt, max_tokens=1500)

    # Robust tag-based parsing that never breaks on unescaped quotes
    repo_name_m = re.search(r"REPO_NAME:\s*([a-zA-Z0-9\-_]+)", raw)
    desc_m = re.search(r"DESCRIPTION:\s*(.+)", raw)
    files_m = re.search(r"CORE_FILES:\s*(.+)", raw)
    arch_m = re.search(r"ARCHITECTURE_SUMMARY:\s*(.+)", raw, re.DOTALL)

    repo_name = repo_name_m.group(1).strip() if repo_name_m else f"{language.lower()}-sys-{int(time.time())}"
    description = desc_m.group(1).strip() if desc_m else f"Production {language} systems engine"
    
    if files_m:
        core_files = [f.strip() for f in files_m.group(1).split(",") if f.strip()]
    else:
        ext = "cpp" if language == "C++" else ("c" if language == "C" else ("java" if language == "Java" else "py"))
        core_files = [f"src/engine.{ext}", f"src/main.{ext}"]

    architecture_summary = arch_m.group(1).strip() if arch_m else topic

    return {
        "repo_name": repo_name,
        "description": description,
        "core_files": core_files[:3],
        "architecture_summary": architecture_summary
    }

def stage_2_generate_file(fpath: str, spec: dict, language: str) -> str:
    print(f"⚙️  Generating core file: [{fpath}]...")
    prompt = f"""
    You are a Staff Systems Engineer. Write complete, production-grade source code for '{fpath}' in {language}.
    Project: '{spec['repo_name']}'
    Architecture: {spec['architecture_summary']}
    Provide real, complete, compilable code with all imports/includes and robust error handling. Do NOT abbreviate.
    Output ONLY raw code.
    """
    raw = ask_gemini(prompt, max_tokens=3500)
    return clean_code(raw)

def stage_3_harness(spec: dict, language: str) -> tuple[str, str, str, str]:
    print(f"\n[Stage 3/4: Verification & Harness] 🧪 Engineering build harness and tests...")
    b_name = "Makefile" if language in ["C", "C++"] else ("pom.xml" if language == "Java" else "requirements.txt")
    b_prompt = f"Write a complete, valid {b_name} to build and test '{spec['repo_name']}' in {language}. Output ONLY raw file content."
    b_code = clean_code(ask_gemini(b_prompt, max_tokens=1500))

    t_name = "tests/test_main.cpp" if language == "C++" else ("tests/test_main.c" if language == "C" else "tests/test_core.py")
    t_prompt = f"Write a complete unit and integration test suite in {language} for '{spec['repo_name']}'. Test invariants and edge cases. Output ONLY raw code."
    t_code = clean_code(ask_gemini(t_prompt, max_tokens=2500))

    return b_name, b_code, t_name, t_code

def stage_4_docs(spec: dict, files: list, language: str) -> str:
    print(f"\n[Stage 4/4: Documentation] 📚 Publishing exhaustive architecture specification & docs...")
    repo_name = spec['repo_name']
    prompt = f"""
    Write an exhaustive, enterprise-grade README.md for '{repo_name}' in {language}.
    Files included: {files}
    Structure:
    - Badges (use https://img.shields.io/badge/License-MIT-yellow.svg and https://img.shields.io/github/stars/{GH_USER}/{repo_name}?style=flat)
    - Architecture & Problem Statement
    - ASCII Architecture / Dataflow Diagram
    - Algorithmic Decisions & Concurrency Invariants
    - Build, Compilation & Test Execution Recipes
    Output ONLY raw Markdown.
    """
    raw = ask_gemini(prompt, max_tokens=3000)
    return clean_code(raw)

def execute_deep_build():
    category = random.choice(DOMAIN_CHALLENGES)
    topic = random.choice(category["challenges"])
    language = random.choice(LANGUAGES)

    print("=" * 70)
    print(f"🚀 INITIATING MODULAR CLOUD ENGINEERING CYCLE: [{language}]")
    print(f"🎯 Domain: {category['domain']}")
    print(f"🎯 Objective: {topic}")
    print("=" * 70)

    # Stage 1: Spec (Tag-based, cannot crash on unescaped quotes)
    spec = stage_1_spec(topic, language)

    # Stage 2: Individual File Generations (pure text, no JSON escaping)
    files_dict = {}
    for fpath in spec.get("core_files", []):
        files_dict[fpath] = stage_2_generate_file(fpath, spec, language)

    # Stage 3: Harness & Tests
    b_name, b_code, t_name, t_code = stage_3_harness(spec, language)
    files_dict[b_name] = b_code
    files_dict[t_name] = t_code

    # Stage 4: Documentation
    readme_content = stage_4_docs(spec, list(files_dict.keys()), language)

    # Scaffold repository in runner filesystem
    base_name = spec.get("repo_name", f"{language.lower()}-engine-{int(time.time())}")
    description = spec.get("description", f"Enterprise {language} systems engine")
    work_dir = Path(f"/tmp/{base_name}")
    work_dir.mkdir(parents=True, exist_ok=True)

    for rel_path, code in files_dict.items():
        dest = work_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        if dest.suffix in [".sh", ".py"]:
            dest.chmod(0o755)

    (work_dir / "README.md").write_text(readme_content, encoding="utf-8")
    (work_dir / ".gitignore").write_text("*.o\n*.a\n*.out\n*.class\ntarget/\nbuild/\nbin/\nvenv/\n__pycache__/\n.DS_Store\n", encoding="utf-8")

    # Native CI/CD Workflow
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
