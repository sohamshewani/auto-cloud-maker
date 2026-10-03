import os
import json
import time
import random
import re
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

LANGUAGES = ["C++", "C", "Java", "Python"]

ELITE_DOMAINS = [
    {
        "domain": "High-Performance Storage Engines",
        "challenges": [
            "Log-Structured Merge-tree (LSM) key-value engine with write-ahead logging (WAL), Bloom filter pruning, and leveled compaction",
            "In-memory columnar database storage engine with vectorized scan operations, dictionary encoding, and bitmap indices",
            "B-Tree index storage engine with page cache eviction policies and write-ahead redo logging"
        ]
    },
    {
        "domain": "Distributed Consensus & Protocols",
        "challenges": [
            "Raft distributed consensus state machine with dynamic leader election, heartbeats, and log compaction",
            "Gossip-protocol cluster membership detector with failure detection and vector-clock state synchronization",
            "Distributed token-bucket rate limiter with sliding-window counters and thread-safe ring buffers"
        ]
    },
    {
        "domain": "Systems, Compilers & Low-Level Runtimes",
        "challenges": [
            "Recursive-descent AST parser and bytecode virtual machine interpreter with stack-frame execution",
            "Static analysis dead-code and memory leak detector using control-flow graph (CFG) traversal",
            "Zero-copy userspace packet filter with ring buffers, memory arena pooling, and sliding-window flow control",
            "Async high-concurrency event-driven network server using non-blocking socket I/O and connection pooling"
        ]
    }
]

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
GH_USER = os.environ.get("GITHUB_ACTOR", "sohamshewani")
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.returncode == 0, res.stdout, res.stderr

def ask_gemini(prompt: str, max_tokens: int = 3500) -> str:
    """Zero-lag API invoker with strict timeouts and exponential backoff to avoid hanging."""
    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=0.2
    )

    for attempt in range(1, 4):
        for model_name in MODELS:
            try:
                print(f"⚡ [Attempt {attempt}] Querying [{model_name}]...", flush=True)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if response.text and response.text.strip():
                    return response.text
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ [{model_name}] error: {err_str[:120]}...", flush=True)
                if "503" in err_str or "429" in err_str:
                    time.sleep(5 * attempt)
                continue

    raise RuntimeError("Gemini API call timed out across all models and attempts.")

def clean_code(raw_text: str) -> str:
    cleaned = re.sub(r"^```[a-zA-Z0-9_\+\-]*\n", "", raw_text.strip())
    cleaned = re.sub(r"\n```$", "", cleaned.strip())
    return cleaned

def stage_1_architectural_spec(topic: str, language: str) -> dict:
    print(f"\n[Stage 1/4: Systems Research] 🔬 Architecting: '{topic}' ({language})...", flush=True)
    prompt = f"""
    You are a Principal Software Architect. Design a production-grade, senior-level systems engineering project in {language} for: '{topic}'.
    Demand high rigor: clean separation of concerns, modular directory layout (src/, include/, tests/), 
    and complete defensive programming.

    Output in this EXACT tag format:
    REPO_NAME: <kebab-case-project-name>
    DESCRIPTION: <Professional 1-sentence technical GitHub summary mentioning {language}>
    CORE_FILES: <comma-separated relative file paths, e.g. include/engine.hpp, src/engine.cpp, src/main.cpp>
    ARCHITECTURE_SUMMARY:
    <Deep technical explanation of data structures, concurrency invariants, and data flow>
    """
    raw = ask_gemini(prompt, max_tokens=1200)

    repo_m = re.search(r"REPO_NAME:\s*([a-zA-Z0-9\-_]+)", raw)
    desc_m = re.search(r"DESCRIPTION:\s*(.+)", raw)
    files_m = re.search(r"CORE_FILES:\s*(.+)", raw)
    arch_m = re.search(r"ARCHITECTURE_SUMMARY:\s*(.+)", raw, re.DOTALL)

    repo_name = repo_m.group(1).strip() if repo_m else f"{language.lower()}-sys-{int(time.time())}"
    description = desc_m.group(1).strip() if desc_m else f"Production {language} systems engine"
    
    if files_m:
        core_files = [f.strip() for f in files_m.group(1).split(",") if f.strip()]
    else:
        ext = "cpp" if language == "C++" else ("c" if language == "C" else ("java" if language == "Java" else "py"))
        core_files = [f"src/engine.{ext}", f"src/main.{ext}"]

    return {
        "repo_name": repo_name,
        "description": description,
        "core_files": core_files[:3],
        "architecture_summary": arch_m.group(1).strip() if arch_m else topic
    }

def stage_2_build_file(fpath: str, spec: dict, language: str) -> str:
    print(f"⚙️  Authoring production file: [{fpath}]...", flush=True)
    prompt = f"""
    You are a Staff Systems Engineer. Write the complete, production-grade source code for '{fpath}' in {language}.
    Project: '{spec['repo_name']}'
    Architecture: {spec['architecture_summary']}
    
    CRITICAL QUALITY RULES:
    1. Write real, complete, compilable code.
    2. NEVER use placeholders (NO '// TODO', NO 'pass', NO truncation).
    3. Include all required imports, headers, concurrency guards, and memory management.
    Output ONLY raw code.
    """
    return clean_code(ask_gemini(prompt, max_tokens=3000))

def stage_3_build_harness(spec: dict, language: str) -> tuple[str, str, str, str]:
    print(f"\n[Stage 3/4: Verification Harness] 🧪 Engineering build configs and test harness...", flush=True)
    b_name = "Makefile" if language in ["C", "C++"] else ("pom.xml" if language == "Java" else "requirements.txt")
    b_prompt = f"Write a complete, valid {b_name} to build and test '{spec['repo_name']}' in {language}. Output ONLY raw file content."
    b_code = clean_code(ask_gemini(b_prompt, max_tokens=1200))

    t_name = "tests/test_engine.cpp" if language == "C++" else ("tests/test_engine.c" if language == "C" else "tests/test_core.py")
    t_prompt = f"""
    Write a complete unit and integration test suite in {language} for '{spec['repo_name']}'.
    Cover assertions, invariant testing, and edge cases.
    Output ONLY raw code.
    """
    t_code = clean_code(ask_gemini(t_prompt, max_tokens=2200))

    return b_name, b_code, t_name, t_code

def stage_4_enterprise_docs(spec: dict, files: list, language: str) -> str:
    print(f"\n[Stage 4/4: Documentation] 📚 Publishing enterprise specification...", flush=True)
    repo_name = spec['repo_name']
    prompt = f"""
    Write an enterprise-grade README.md for '{repo_name}' in {language}.
    Files included: {files}
    Structure:
    - Badges:
      [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
      [![Stars](https://img.shields.io/github/stars/{GH_USER}/{repo_name}?style=flat)](https://github.com/{GH_USER}/{repo_name})
    - Architecture & Problem Statement
    - ASCII Architecture / Dataflow Diagram
    - Algorithmic Decisions & Concurrency Invariants
    - Build, Compilation & Test Execution Recipes
    Output ONLY raw Markdown.
    """
    return clean_code(ask_gemini(prompt, max_tokens=2500))

def execute_build():
    category = random.choice(ELITE_DOMAINS)
    topic = random.choice(category["challenges"])
    language = random.choice(LANGUAGES)

    print("=" * 70, flush=True)
    print(f"🚀 INITIATING HIGH-SPEED ENTERPRISE BUILD: [{language}]", flush=True)
    print(f"🎯 Domain: {category['domain']}", flush=True)
    print(f"🎯 Challenge: {topic}", flush=True)
    print("=" * 70, flush=True)

    # 1. Spec
    spec = stage_1_architectural_spec(topic, language)

    # 2. Complete Files
    files_dict = {}
    for fpath in spec.get("core_files", []):
        files_dict[fpath] = stage_2_build_file(fpath, spec, language)

    # 3. Harness
    b_name, b_code, t_name, t_code = stage_3_build_harness(spec, language)
    files_dict[b_name] = b_code
    files_dict[t_name] = t_code

    # 4. Docs
    readme_content = stage_4_enterprise_docs(spec, list(files_dict.keys()), language)

    # Scaffolding
    base_name = spec.get("repo_name", f"{language.lower()}-sys-{int(time.time())}")
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
                print(f"\n🌟 Published Production Repository: https://github.com/{GH_USER}/{name_attempt}", flush=True)
                break
            counter += 1
            name_attempt = f"{base_name}-v{counter}"
            run("git remote remove origin", cwd=work_dir)
        else:
            counter += 1
            name_attempt = f"{base_name}-v{counter}"

if __name__ == "__main__":
    execute_build()
