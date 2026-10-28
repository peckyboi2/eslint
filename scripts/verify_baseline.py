#!/usr/bin/env python3
"""Check Milestone A/B integrity; no inference, network or report-code execution."""

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "clarifier"))
from constants import CONFIG_PATHS, CONFIG_PATH, MODULE_NAMES, SKILL_PATH
from recording import load_configuration


ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "161558ae1391a8649a8d69a8b2c2e555b40121b9"
GOLDEN_DIGEST = "fa64d12b7c6db060be0a269200bb3e288c37a71fbe7d36df7769462466e51085"
ALLOWED_MODIFICATIONS = {
    "AGENTS.md", "CONTRIBUTING.md", "README.md", ".gitattributes", ".gitignore", ".prettierignore"
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check_manifest(folder, entries):
    for relative, expected in entries.items():
        name = PurePosixPath(relative)
        path = folder / relative
        if name.is_absolute() or ".." in name.parts or path.is_symlink():
            raise ValueError(f"Unsafe evidence path: {relative}")
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError(f"Evidence path escapes its folder: {relative}")
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Missing or changed evidence: {relative}")


def check_configuration(folder):
    """Verify retained settings and the recorded source-hash identity."""
    path = folder / "configuration-hashes.json"
    if not path.exists():
        return
    manifest = read_json(path)
    check_manifest(folder / "configuration", manifest["files"])
    sources = manifest.get("source_hashes", {})
    if set(sources) & set(manifest["files"]):
        raise ValueError("Retained files and source identifiers overlap")
    hashes = {**manifest["files"], **sources}
    if any(len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value) for value in hashes.values()):
        raise ValueError("Invalid configuration digest")
    canonical = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    aggregate = hashlib.sha256(canonical.encode()).hexdigest()
    if aggregate != manifest["aggregate_sha256"]:
        raise ValueError("Configuration aggregate differs from recorded identity")
    if aggregate != read_json(folder / "record.json")["configuration_sha256"]:
        raise ValueError("Run does not reference recorded configuration identity")


def check_evidence_archive(path):
    """Verify an optional data-only development bundle without importing old code."""
    if not path.exists():
        return 0
    if path.is_symlink():
        raise ValueError("Evidence archive cannot be a symbolic link")
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if (not member.isfile() or name.is_absolute() or ".." in name.parts
                    or member.name.lower().endswith((".py", ".pyc", ".pyo"))):
                raise ValueError("Evidence bundle must contain data files only")
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate evidence archive path")
        manifest = json.load(archive.extractfile("manifest.json"))
        if set(names) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("Evidence archive inventory mismatch")
        for name, expected in manifest["files"].items():
            if hashlib.sha256(archive.extractfile(name).read()).hexdigest() != expected:
                raise ValueError("Development evidence hash mismatch")
        return len(manifest["files"])


def main():
    golden = ROOT / "evals/golden"
    if any(p.is_symlink() for p in golden.rglob("*")):
        raise ValueError("Golden evidence must not contain symbolic links")
    freeze = read_json(golden / "FREEZE.json")
    check_manifest(golden, freeze["files"])
    actual = {
        p.relative_to(golden).as_posix()
        for p in golden.rglob("*")
        if p.is_file() and p != golden / "FREEZE.json"
    }
    if actual != set(freeze["files"]):
        raise ValueError("Golden inventory differs from the frozen file set")
    canonical = json.dumps(freeze["files"], sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode()).hexdigest() != GOLDEN_DIGEST:
        raise ValueError("Golden aggregate differs from accepted golden-v1")
    if freeze["aggregate_sha256"] != GOLDEN_DIGEST:
        raise ValueError("Freeze record has an incorrect aggregate digest")
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"], cwd=ROOT,
        input="\n".join("evals/golden/" + p for p in freeze["files"]) + "\n",
        text=True, capture_output=True, check=False,
    )
    if ignored.returncode not in (0, 1) or ignored.stdout.strip():
        raise ValueError(f"Frozen files would be omitted by Git: {ignored.stdout.strip()}")

    packages = golden / "prepared-inputs"
    check_manifest(packages, read_json(packages / "SHA256-MANIFEST.json"))
    cases = read_json(packages / "manifest.json")["cases"]
    expected = read_json(golden / "expectations.json")["cases"]
    ids = {case["issue"] for case in cases}
    if len(cases) != 10 or len(expected) != 10 or len(ids) != 10:
        raise ValueError("Expected ten unique case packages and expectations")
    if ids != {row["issue"] for row in expected}:
        raise ValueError("Case and expectation identifiers differ")
    sizes = {}
    for case in cases:
        folder = packages / case["folder"]
        if digest(folder / "body.md") != case["body_sha256"]:
            raise ValueError(f"Historical body mismatch: {case['issue']}")
        sizes[str(case["issue"])] = sum(
            p.stat().st_size for p in folder.rglob("*") if p.is_file()
        )
        if sizes[str(case["issue"])] > 65536:
            raise ValueError(f"Package exceeds 64 KiB: {case['issue']}")

    original_paths = set(git("ls-tree", "-r", "--name-only", BASE_COMMIT).splitlines())
    all_changes = set(filter(None, git("diff", "--name-only", BASE_COMMIT).splitlines()))
    changed = all_changes & original_paths
    if changed - ALLOWED_MODIFICATIONS:
        raise ValueError(f"Unexpected upstream changes: {sorted(changed - ALLOWED_MODIFICATIONS)}")
    added = (all_changes - original_paths) | set(filter(None, git(
        "ls-files", "--others", "--exclude-standard"
    ).splitlines()))
    unexpected = {
        p for p in added
        if not (p.startswith("evals/golden/")
                or p.startswith(("evals/runs/", "evals/platform-tests/", "evals/checks/"))
                or p in {path.as_posix() for path in CONFIG_PATHS}
                or p in {f"scripts/clarifier/tests/test_{name}.py" for name in MODULE_NAMES}
                or p == "scripts/clarifier/tests/__init__.py"
                or p in {"evals/development-evidence.tar.gz",
                         "scripts/clarifier/tests/fixtures/routing.json",
                         "scripts/verify_baseline.py", "scripts/clarifier/preview.py",
                         "scripts/clarifier/transport.py",
                         "scripts/clarifier/config.json", "scripts/clarifier/decision.schema.json",
                         ".claude/skills/eslint-clarification/SKILL.md"})
    }
    if unexpected:
        raise ValueError(f"Unexpected assignment additions: {sorted(unexpected)}")
    if any(not (ROOT / p).is_file() for p in ALLOWED_MODIFICATIONS):
        raise ValueError("An original instruction/configuration file is missing")
    original_workflows = set(git(
        "ls-tree", "-r", "--name-only", BASE_COMMIT, ".github/workflows"
    ).splitlines())
    current_workflows = {
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / ".github/workflows").rglob("*") if p.is_file()
    }
    if original_workflows != current_workflows:
        raise ValueError("Inherited workflow inventory changed")
    if set((ROOT / ".claude").rglob("SKILL.md")) != {
        ROOT / ".claude/skills/eslint-clarification/SKILL.md"
    }:
        raise ValueError("Unexpected canonical skill inventory")
    config = load_configuration(ROOT / CONFIG_PATH)
    if digest(ROOT / SKILL_PATH) != config["skill_sha256"]:
        raise ValueError("Active skill differs from configured digest")
    evidence_count = check_evidence_archive(ROOT / "evals/development-evidence.tar.gz")
    run_counts = {"actual": 0, "platform": 0}
    for kind, key in (("runs", "actual"), ("platform-tests", "platform")):
        folders = list((ROOT / "evals" / kind).glob("*"))
        if len({folder.name for folder in folders}) != len(folders):
            raise ValueError("Duplicate run identity")
        for folder in folders:
            if folder.is_symlink() or not folder.is_dir():
                raise ValueError("Unsafe run directory")
            inventory = read_json(folder / "artifact-hashes.json")
            check_manifest(folder, inventory)
            check_configuration(folder)
            actual_files = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
            allowed_files = set(inventory) | {"artifact-hashes.json", "comparison.json"}
            if actual_files - allowed_files:
                raise ValueError("Unexpected files added to a recorded run")
            comparison_path = folder / "comparison.json"
            if comparison_path.exists():
                comparison = read_json(comparison_path)
                if comparison["raw_output_sha256"] != digest(folder / "raw-output.txt"):
                    raise ValueError("Comparison does not reference the recorded output")
                if comparison["configuration_sha256"] != read_json(folder / "record.json")["configuration_sha256"]:
                    raise ValueError("Comparison does not reference the recorded configuration")
            for path in folder.rglob("*"):
                if path.is_symlink() or path.name in {"auth.json", "credentials", "credentials.json"}:
                    raise ValueError("Unsafe file in run record")
            run_counts[key] += 1

    if git("remote", "get-url", "origin") != "https://github.com/peckyboi2/eslint.git":
        raise ValueError("Unexpected origin")

    print(json.dumps({
        "result": "PASS",
        "verification_type": "static integrity; no inference/network/report-code execution",
        "golden_version": freeze["version"],
        "golden_aggregate_sha256": GOLDEN_DIGEST,
        "frozen_files_verified": len(freeze["files"]),
        "frozen_files_ignored_by_git": 0,
        "case_package_bytes": sizes,
        "upstream_base_commit": BASE_COMMIT,
        "original_tracked_files": len(original_paths),
        "modified_upstream_paths": sorted(changed),
        "inherited_workflows_unchanged": len(original_workflows),
        "live_actions_setting_requeried": False,
        "recorded_actual_attempts": run_counts["actual"],
        "recorded_platform_attempts": run_counts["platform"],
        "development_evidence_files": evidence_count,
        "current_configuration_version": config["version"],
        "current_model": config["model"],
        "current_reasoning_effort": config["reasoning_effort"],
        "posting_tests": 0,
        "runtime_isolation_retested_by_this_check": False,
    }, indent=2))


if __name__ == "__main__":
    main()
