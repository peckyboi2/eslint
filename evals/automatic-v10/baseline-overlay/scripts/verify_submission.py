#!/usr/bin/env python3
"""Verify the complete packaged submission offline; never invoke an agent or network."""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote

import verify_baseline as historical
import check_v9_attacks as supplemental
from clarifier.inference import packages, staging
from clarifier.inference.recording import load_configuration
from clarifier.outputs import campaign, campaign_metrics
from clarifier.shared import constants as c
from clarifier.shared.errors import ClarifierError


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_CANDIDATE = "884acc7031a761eb45e5fe7ac186d43d5bed5901"
FINAL = "evals/checks/gate-f-20261028"
G_PRESERVED = "evals/checks/gate-g-20261028/preserved-evidence-sha256.json"
BUNDLE = "evals/golden/final-results-v9"
GOLDEN_FREEZE_SHA = "f5a4d84dc59728cbec961eae309ca0df0328cfbb1b9b3747a16d3584987d8d20"
FINAL_FREEZE_SHA = "0c0ca76cd19e5adca0c5ebfc2be40e531a1ecbda5a4a546ada9f42d125d21a5f"
G_PRESERVED_SHA = "6022e3d9f60bafa7e074b89347008620b43f597e76b1fef8b5eb0238757df041"
EXPORT_MANIFEST_SHA = "711a27974bc59feb03c59fb0be177c98af12ae9e179e0159f62bc080f44c9950"
SUPPLEMENT_PLAN_SHA = "16c4c8ba9f9fe09929bba80cbacbd5fbd3949471f1f8cebdb4a2f9320545a554"
SUPPLEMENT_MANIFEST_SHA = "81486c945ae438e89e3b1be0283ff1b48f87906616ecd0b525bc0f45279d64c9"
CURRENT_DOCS = ("SUBMISSION.md", "DESIGN.md", "evals/README.md",
                "evals/golden/INDEX.md", f"{BUNDLE}/README.md",
                str(supplemental.FOLDER / "README.md"))
EDITABLE_ORIGINALS = {"DESIGN.md", "evals/README.md"}
NEW_FILES = {"SUBMISSION.md", "scripts/verify_submission.py",
             "scripts/check_v9_attacks.py",
             "scripts/submission_tests/test_verify_submission.py", "evals/golden/INDEX.md",
             f"{BUNDLE}/README.md", f"{BUNDLE}/.gitattributes", f"{BUNDLE}/exports.json"}
REPORT_FOLDER = "evals/submission-checks-v1"
REPORTS = {f"{REPORT_FOLDER}/{name}" for name in (
    "verification.json", "verifier-tests.txt", "verifier-tests-initial.txt",
    "test-isolation-note.md", "safety-tests.txt", "SHA256-MANIFEST.json")}
RUN_EXPORTS = ("raw-output.txt", "transcript.jsonl", "record.json", "validation.json")


class SubmissionError(ValueError):
    """The complete submission cannot be verified without changing evidence."""


def require(passed: bool, reason: str) -> None:
    """Raise SubmissionError when a required invariant fails."""
    if not passed:
        raise SubmissionError(reason)


def read_json(path: Path) -> dict:
    """Return saved JSON or raise on malformed or missing bytes."""
    return json.loads(path.read_text(encoding="utf-8"))


def git(root: Path, *args: str) -> str:
    """Return local read-only Git output or raise on failure."""
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def pinned_json(root: Path, name: str, expected: str) -> dict:
    """Return hash-pinned JSON or raise on changed or unsafe evidence."""
    path = root / name
    historical.check_manifest(root, {name: expected})
    return read_json(path)


def tree_files(root: Path) -> set[str]:
    """Inventory every working-tree file, including ignored files; reject symlinks."""
    found = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if relative.parts[0] == ".git":
            continue
        require(not path.is_symlink(), f"Symlink in submission: {relative}")
        if path.is_file():
            found.add(relative.as_posix())
        else:
            require(path.is_dir(), f"Nonregular submission path: {relative}")
    return found


def export_sources(root: Path, frozen: dict) -> dict[str, str]:
    """Define the selected byte-for-byte exports independently of their manifest."""
    sources = {}
    for row in frozen["cases"]:
        for name in RUN_EXPORTS:
            sources[f"final/{row['run_id']}/{name}"] = f"evals/runs/{row['run_id']}/{name}"
        name = f"comparisons/{row['issue']}.json"
        sources[name] = f"{FINAL}/{name}"
    for name in ("comparison.json", "semantic-reviews.json", "pre-freeze-tests-v3.txt"):
        sources[f"checks/{name}"] = f"{FINAL}/{name}"
    review_path = "evals/checks/gate-e-20261028/task47-v8-attack-review.json"
    sources["adversarial/review-v8.json"] = review_path
    for row in read_json(root / review_path)["runs"]:
        for name in RUN_EXPORTS:
            sources[f"adversarial/{Path(row['run']).name}/{name}"] = f"{row['run']}/{name}"
    return sources


def check_tree(root: Path, actual: set[str], additions: set[str]) -> int:
    """Preserve the entire reviewed candidate, allowing only two current-doc edits."""
    original = set(git(root, "ls-tree", "-r", "--name-only", ORIGINAL_CANDIDATE).splitlines())
    require(len(original) == 5221, "Original candidate tree unavailable or unexpected")
    missing = original - actual
    require(not missing, f"Original candidate files missing: {sorted(missing)}")
    changes = set(git(root, "diff", "--name-only", ORIGINAL_CANDIDATE, "--").splitlines())
    unexpected_changes = (changes & original) - EDITABLE_ORIGINALS
    require(not unexpected_changes, f"Original candidate changed: {sorted(unexpected_changes)}")
    require(additions <= actual, f"Required packaging missing: {sorted(additions - actual)}")
    unexpected = actual - original - additions - REPORTS
    require(not unexpected, f"Unexpected submission additions: {sorted(unexpected)}")
    require(git(root, "remote", "get-url", "origin") == "https://github.com/peckyboi2/eslint.git",
            "Unexpected origin (no remote access is performed)")
    return len(original)


def check_historical_runs(root: Path) -> dict[str, int]:
    counts = {}
    for kind in ("runs", "platform-tests"):
        folders = list((root / "evals" / kind).iterdir())
        for folder in folders:
            require(folder.is_dir(), f"Unsafe recorded run: {folder.name}")
            inventory = read_json(folder / "artifact-hashes.json")
            historical.check_manifest(folder, inventory)
            historical.check_configuration(folder)
            actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
            require(not actual - set(inventory) - {"artifact-hashes.json", "comparison.json"},
                    f"Unexpected recorded run files: {folder.name}")
            for path in folder.rglob("*"):
                require(path.name not in {"auth.json", "credentials", "credentials.json"},
                        "Credentials in retained run")
            if (folder / "comparison.json").exists():
                comparison = read_json(folder / "comparison.json")
                require(comparison["raw_output_sha256"] == historical.digest(folder / "raw-output.txt")
                        and comparison["configuration_sha256"] == read_json(folder / "record.json")["configuration_sha256"],
                        f"Historical comparison binding differs: {folder.name}")
        counts[kind] = len(folders)
    return counts


def check_links(root: Path) -> int:
    """Return the checked local-link count or raise on missing current navigation."""
    count = 0
    for name in CURRENT_DOCS:
        content = (root / name).read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            target = unquote(target.strip("<>"))
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            path = ((root / name).parent / target.split("#", 1)[0]).resolve()
            require(path.is_relative_to(root.resolve()) and path.exists(), f"Broken local link: {name} -> {target}")
            count += 1
    require("evals/golden/INDEX.md" in (root / "SUBMISSION.md").read_text(), "Missing current golden entry point")
    for name in ("SUBMISSION.md", "evals/golden/INDEX.md", "evals/README.md"):
        require("python3 -B scripts/verify_submission.py" in (root / name).read_text(),
                f"Current validation command missing: {name}")
    require(len((root / "DESIGN.md").read_text().splitlines()) <= 150, "DESIGN.md exceeds 150 lines")
    return count


@contextmanager
def disposable_copy(root: Path):
    """Copy current bytes into a disposable local Git clone, with no remote access."""
    with tempfile.TemporaryDirectory(prefix="cs467-submission-copy-", dir=c.PRIVATE_TEMP_ROOT) as folder:
        destination = Path(folder) / "submission"
        subprocess.run(["git", "clone", "--shared", "--no-checkout", "--quiet", str(root), str(destination)],
                       check=True, capture_output=True)
        subprocess.run(["git", "read-tree", "HEAD"], cwd=destination, check=True, capture_output=True)
        subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/peckyboi2/eslint.git"],
                       cwd=destination, check=True, capture_output=True)
        for name in tree_files(root):
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
        (destination / REPORT_FOLDER).mkdir(exist_ok=True)
        yield destination


def check_freezes(root: Path) -> tuple[dict, dict]:
    """Return verified golden/final freezes or raise on any original hash change."""
    golden = pinned_json(root, "evals/golden/FREEZE.json", GOLDEN_FREEZE_SHA)
    frozen = pinned_json(root, f"{FINAL}/freeze.json", FINAL_FREEZE_SHA)
    retained = pinned_json(root, G_PRESERVED, G_PRESERVED_SHA)
    historical.check_manifest(root / "evals/golden", golden["files"])
    require(campaign.digest_map(golden["files"]) == golden["aggregate_sha256"] == historical.GOLDEN_DIGEST,
            "Golden-v1 aggregate differs")
    require(len(frozen["files"]) == 168 and len(retained) == 2710, "Historical inventory count differs")
    campaign.verify_files(root, frozen["files"])
    campaign.verify_files(root, retained)
    return golden, frozen


def check_golden_layout(root: Path, actual: set[str], golden: dict, additions: set[str]) -> None:
    """Raise on unlisted golden files or required packaging ignored by Git."""
    golden_paths = {"evals/golden/FREEZE.json"} | {"evals/golden/" + name for name in golden["files"]}
    require({name for name in actual if name.startswith("evals/golden/")} == golden_paths | {
        name for name in additions if name.startswith("evals/golden/")}, "Golden inventory differs from original plus named bundle")
    ignored = subprocess.run(["git", "check-ignore", "--no-index", "--stdin"], cwd=root,
                             input="\n".join(sorted(golden_paths | additions)) + "\n", text=True, capture_output=True)
    require(ignored.returncode in (0, 1) and not ignored.stdout.strip(), "Required packaging ignored by Git")


def check_exports(root: Path, sources: dict[str, str], frozen: dict) -> None:
    """Raise on changed export provenance, bytes or checkout text conversion."""
    manifest = pinned_json(root, f"{BUNDLE}/exports.json", EXPORT_MANIFEST_SHA)
    require(manifest["source_commit"] == ORIGINAL_CANDIDATE and manifest["campaign_id"] == frozen["campaign_id"],
            "Export provenance differs")
    require({name: row["source"] for name, row in manifest["exports"].items()} == sources,
            "Export source inventory differs")
    for name, row in manifest["exports"].items():
        historical.check_manifest(root, {row["source"]: row["sha256"], f"{BUNDLE}/{name}": row["sha256"]})
        require((root / row["source"]).read_bytes() == (root / BUNDLE / name).read_bytes(), "Export bytes differ")
    require((root / BUNDLE / ".gitattributes").read_text() == "* -text -whitespace\n", "Export byte-preservation attributes differ")
    attrs = subprocess.check_output(["git", "check-attr", "text", "--", *[f"{BUNDLE}/{name}" for name in sources]], cwd=root, text=True)
    require(all(line.endswith(": text: unset") for line in attrs.splitlines()), "Export text conversion enabled")


def check_configuration(root: Path, frozen: dict) -> None:
    """Raise on any changed historical package or active configuration identity."""
    historical.check_manifest(root / c.PREPARED_PATH, read_json(root / c.PREPARED_PATH / "SHA256-MANIFEST.json"))
    config = load_configuration(root / c.CONFIG_PATH)
    require(campaign.digest_map({str(p): historical.digest(root / p) for p in c.CONFIG_PATHS}) == frozen["configuration_sha256"],
            "Evaluated configuration identity differs")
    require(historical.digest(root / c.SKILL_PATH) == config["skill_sha256"], "Canonical skill differs")


def check_staged_inputs(root: Path, frozen: dict) -> None:
    """Stage ten disposable closed input packages or raise before any inference."""
    with tempfile.TemporaryDirectory(prefix="cs467-submission-", dir=c.PRIVATE_TEMP_ROOT) as folder:
        for case in frozen["cases"]:
            package = packages.load(case["issue"], root)
            staged = staging.stage(package.source, Path(folder) / str(case["issue"]), expected=package.hashes)
            require(staged["source_hashes"] == case["input_hashes"], "Staged historical input differs")


def reproduce_comparison(root: Path, frozen: dict) -> dict:
    """Return the exact saved 9/10 comparison or raise on changed outcomes."""
    expected = {row["issue"]: row["decision"] for row in read_json(root / "evals/golden/expectations.json")["cases"]}
    require(len(expected) == 10 and list(frozen["case_order"]) == list(c.HISTORICAL_CASE_IDS), "Ten-case identity differs")
    reviews = read_json(root / FINAL / "semantic-reviews.json")
    observed = [campaign.inspect_case(root, frozen, case) for case in frozen["cases"]]
    rows = [campaign_metrics.compare_case(row, expected[row["issue"]], review)
            for row, review in zip(observed, reviews, strict=True)]
    reproduced = campaign_metrics.aggregate(rows, frozen["campaign_id"], frozen["configuration_sha256"])
    require(reproduced == read_json(root / FINAL / "comparison.json"), "Saved final comparison not faithfully reproduced")
    for row in rows:
        require(row == read_json(root / FINAL / f"comparisons/{row['issue']}.json"), "Per-case comparison differs")
    require(reproduced["metrics"]["decision_matches"] == {"count": 9, "denominator": 10}
            and [row["issue"] for row in rows if not row["decision_pass"]] == [19924], "Recorded 9/10 failure changed")
    return reproduced


def check_saved_reports(root: Path) -> None:
    """Verify optional saved check logs or raise on an incomplete/changed manifest."""
    report_manifest = root / REPORT_FOLDER / "SHA256-MANIFEST.json"
    if report_manifest.exists():
        reports = read_json(report_manifest)
        require(set(reports) == {Path(name).name for name in REPORTS} - {"SHA256-MANIFEST.json"},
                "Verification-log inventory differs")
        historical.check_manifest(report_manifest.parent, reports)


def build_result(root: Path, golden: dict, sources: dict, original_count: int,
                 archive_count: int, run_counts: dict, reproduced: dict, links: int) -> dict:
    """Return an explicit structural-verification summary, with no new accuracy claim."""
    return dict(result="PASS", verification="complete working tree; offline; no model/network/report-code execution",
                original_candidate=ORIGINAL_CANDIDATE, original_tree_files=original_count,
                original_current_docs_allowed=sorted(EDITABLE_ORIGINALS), golden_v1_files=len(golden["files"]),
                final_frozen_files=168, preserved_earlier_evidence_files=2710, original_freezes_unchanged=True,
                development_archive_files=archive_count, recorded_attempts=run_counts,
                byte_identical_exports=len(sources), isolated_historical_packages=10,
                exact_final_comparison_reproduced=True, decision_matches=reproduced["metrics"]["decision_matches"],
                retained_failed_case=19924, design_lines=len((root / "DESIGN.md").read_text().splitlines()),
                current_local_links=links, model_calls=0,
                scope_limit="Structural replay uses saved semantic assessments; no new judgement or hosted-control verification.")


def verify(root: Path) -> dict:
    """Return complete-tree verification evidence or raise at the first failed check."""
    root = root.resolve()
    actual = tree_files(root)
    golden, frozen = check_freezes(root)
    supplement = supplemental.verify(root, SUPPLEMENT_PLAN_SHA, SUPPLEMENT_MANIFEST_SHA)
    sources = export_sources(root, frozen)
    additions = NEW_FILES | {f"{BUNDLE}/{name}" for name in sources} | set(supplement["files"])
    original_count = check_tree(root, actual, additions)
    check_golden_layout(root, actual, golden, additions)
    check_exports(root, sources, frozen)
    check_configuration(root, frozen)
    archive_count = historical.check_evidence_archive(root / "evals/development-evidence.tar.gz")
    run_counts = check_historical_runs(root)
    check_staged_inputs(root, frozen)
    reproduced = reproduce_comparison(root, frozen)
    check_saved_reports(root)
    links = check_links(root)
    result = build_result(root, golden, sources, original_count, archive_count, run_counts, reproduced, links)
    result["supplemental_v9_attacks"] = {key: value for key, value in supplement.items() if key != "files"}
    return result


def main() -> int:
    """Run the offline CLI and return a nonzero exit status for failed verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--safety-tests", action="store_true",
                        help="Verify, then run the frozen 172-test suite in a disposable local copy")
    args = parser.parse_args()
    try:
        result = verify(ROOT)
        if args.safety_tests:
            # Some historical tests write synthetic platform records beneath their root.
            # Retain their exact source and behavior while keeping this checkout intact.
            with disposable_copy(ROOT) as folder:
                return subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s",
                                       "scripts/clarifier/tests", "-t", "scripts", "-p", "test_*.py", "-v"],
                                      cwd=folder, check=False).returncode
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError, ClarifierError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
