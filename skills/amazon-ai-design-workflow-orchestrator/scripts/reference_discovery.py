"""Stable purpose-based reference discovery, feedback and an opt-in asset library.

These checks establish source/feedback integrity, not aesthetic quality. The
controller inspects candidate images; the user supplies only simple ratings.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

AXES = ("visual", "layout")
POOL = "visual_reference_pool.json"
PENDING = "visual_reference_pool.pending.json"
PROFILE = "visual_preference_profile.json"
DEFAULT_LIBRARY = Path.home() / ".codex/reference-libraries/amazon-design"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def asset_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        raise ValueError("evidence path must be a project-relative path")
    resolved = (root / value).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("evidence path escapes the project")
    if not resolved.is_file():
        raise ValueError(f"evidence does not exist: {value}")
    return resolved


def project_url(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("project_url must be an original project URL")
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("project_url must be an original HTTPS project URL")
        if parsed.path in {"", "/"}:
            raise ValueError("project_url must identify a project, not a homepage")
        query = [(k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith("utm_") and k not in {"fbclid", "gclid"}]
        return urlunsplit(("https", parsed.netloc.lower(), parsed.path.rstrip("/"), urlencode(sorted(query)), ""))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid project_url: {value}") from exc


def check_image(path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        result = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)], capture_output=True, text=True, check=False)
        dimensions = re.findall(r"pixel(?:Width|Height):\s*(\d+)", result.stdout)
        if result.returncode or len(dimensions) != 2:
            raise ValueError("cannot decode reference image; use bundled Pillow Python")
        width, height = map(int, dimensions)
    else:
        try:
            with Image.open(path) as img:
                width, height = img.size
                img.verify()
        except (OSError, ValueError) as exc:
            raise ValueError("cannot decode reference image") from exc
    if width < 240 or height < 160 or max(width / height, height / width) > 12:
        raise ValueError("reference image is too small or too narrow to inspect")


def validate_pool(pool: dict, root: Path) -> list[str]:
    errors = []
    if pool.get("version") != 2:
        errors.append("reference pool version must be 2")
    if not isinstance(pool.get("run_identity"), str) or not pool["run_identity"].strip():
        errors.append("reference pool run_identity is required")
    if type(pool.get("round")) is not int or pool["round"] < 1:
        errors.append("reference pool round must be positive")
    if pool.get("status") not in {"PENDING_RATING", "RATED", "RESEARCH_REQUIRED"}:
        errors.append("invalid reference pool status")
    samples = pool.get("samples")
    if not isinstance(samples, list) or not 1 <= len(samples) <= 12:
        return errors + ["reference pool needs 1-12 candidates; prefer a small useful shortlist"]
    ids, urls, image_owners, coverage = set(), set(), {}, set()
    for sample in samples:
        if not isinstance(sample, dict):
            errors.append("candidate must be an object")
            continue
        sid = sample.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", sid) or sid in ids:
            errors.append("candidate id is missing, unsafe or duplicate")
        else:
            ids.add(sid)
        if not isinstance(sample.get("project"), str) or not sample["project"].strip():
            errors.append(f"{sid}: project title is required")
        try:
            url = project_url(sample.get("project_url"))
            if url in urls:
                errors.append(f"{sid}: duplicate source project; combine its purposes in one card")
            urls.add(url)
        except ValueError as exc:
            errors.append(f"{sid}: {exc}")
        purposes = sample.get("purposes")
        if not isinstance(purposes, list) or not purposes or any(p not in AXES for p in purposes) or len(set(purposes)) != len(purposes):
            errors.append(f"{sid}: purposes must contain visual and/or layout")
            purposes = []
        coverage.update(purposes)
        for axis in AXES:
            value = sample.get(axis)
            if value is not None and (type(value) is not int or value not in {-1, 0, 1}):
                errors.append(f"{sid}: {axis} must be -1, 0, 1 or null")
            if axis not in purposes and value is not None:
                errors.append(f"{sid}: non-applicable {axis} must be null")
        evidence = sample.get("evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 6:
            errors.append(f"{sid}: needs 1-6 actual reference images")
            continue
        evidence_axes = set()
        for item in evidence:
            if not isinstance(item, dict) or item.get("purpose") not in purposes:
                errors.append(f"{sid}: evidence purpose must match the card")
                continue
            evidence_axes.add(item["purpose"])
            try:
                path = asset_path(root, item.get("path"))
                sha = digest(path)
                if item.get("sha256") != sha:
                    raise ValueError("evidence hash mismatch")
                if item.get("source_project_url") is not None and project_url(item["source_project_url"]) != project_url(sample.get("project_url")):
                    raise ValueError("evidence belongs to a different project")
                if sha in image_owners and image_owners[sha] != sid:
                    raise ValueError("duplicate reference image across candidates")
                image_owners[sha] = sid
                check_image(path)
            except (ValueError, OSError) as exc:
                errors.append(f"{sid}: {exc}")
        if set(purposes) - evidence_axes:
            errors.append(f"{sid}: missing evidence for an applicable purpose")
    if set(AXES) - coverage:
        errors.append("reference pool must cover both visual and layout across its candidates")
    if pool.get("status") == "PENDING_RATING":
        errors.extend(_validate_prefilled(pool, root))
    return errors


def _positive_projection(sample: dict) -> dict:
    result = copy.deepcopy(sample)
    result["purposes"] = [a for a in sample["purposes"] if sample.get(a) == 1]
    result["evidence"] = [e for e in result["evidence"] if e["purpose"] in result["purposes"]]
    for axis in AXES:
        if axis not in result["purposes"]:
            result[axis] = None
    return result


def _validate_prefilled(pool: dict, root: Path) -> list[str]:
    prefilled = [s for s in pool.get("samples", []) if isinstance(s, dict) and any(s.get(a) is not None for a in AXES)]
    if not prefilled:
        return []
    if type(pool.get("round")) is not int or pool["round"] <= 1:
        return ["first-round candidates cannot contain prefilled user ratings"]
    try:
        archive = root / "reference-rounds" / f"round-{pool['round'] - 1}"
        previous = read_json(archive / POOL)
        errors = _verify_submission(archive, previous)
        if errors:
            return errors
        if previous.get("run_identity") != pool.get("run_identity") or previous.get("status") != "RESEARCH_REQUIRED":
            return ["carried ratings need the preceding run's search-again receipt"]
        keep_ids = previous.get("research_request", {}).get("preserve_sample_ids", [])
        originals = {s["id"]: s for s in previous["samples"] if s["id"] in keep_ids}
        for sample in prefilled:
            if sample.get("id") not in originals or _positive_projection(originals[sample["id"]]) != sample:
                return ["prefilled ratings do not match the positively rated preserved candidate"]
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return [f"cannot verify carried ratings: {exc}"]
    return []


def _feedback_result(pool: dict, payload: dict) -> dict:
    if payload.get("rater_contract_version") != 2 or payload.get("round") != pool.get("round"):
        raise ValueError("stale or unsupported rating round")
    if payload.get("interaction_mode") == "NATIVE_CHAT_FEEDBACK" and (
        not isinstance(payload.get("user_message"), str) or not payload["user_message"].strip()
    ):
        raise ValueError("native chat feedback needs the explicit user message")
    action = payload.get("action")
    if action not in {"CONTINUE", "RESEARCH_ALL", "RESEARCH_REJECTED"}:
        raise ValueError("unsupported feedback action")
    ratings = payload.get("ratings", [])
    if not isinstance(ratings, list):
        raise ValueError("ratings must be a list")
    by_id = {sample["id"]: sample for sample in pool["samples"]}
    supplied = {}
    for rating in ratings:
        if not isinstance(rating, dict) or rating.get("id") not in by_id or rating["id"] in supplied:
            raise ValueError("rating id is unknown or duplicate")
        supplied[rating["id"]] = rating
    result = copy.deepcopy(pool)
    for sample in result["samples"]:
        rating = supplied.get(sample["id"], {})
        for axis in AXES:
            value = rating.get(axis, sample.get(axis))
            if value is not None and (type(value) is not int or value not in {-1, 0, 1}):
                raise ValueError("rating must be -1, 0, 1 or null")
            if axis not in sample["purposes"] and value is not None:
                raise ValueError("cannot rate a non-applicable purpose")
            if action == "CONTINUE" and axis in sample["purposes"] and value is None:
                raise ValueError("finish applicable ratings or choose to search again")
            sample[axis] = value
    missing = [axis for axis in AXES if not any(s.get(axis) == 1 for s in result["samples"])]
    research = action != "CONTINUE" or bool(missing)
    result["status"] = "RESEARCH_REQUIRED" if research else "RATED"
    result["rating_submission"] = copy.deepcopy(payload)
    result.pop("research_request", None)
    if research:
        kept = [] if action == "RESEARCH_ALL" else [s["id"] for s in result["samples"] if any(s.get(a) == 1 for a in AXES)]
        removed = [s for s in result["samples"] if s["id"] not in kept]
        result["research_request"] = {
            "action": action,
            "preserve_sample_ids": kept,
            "target_purposes": missing or list(AXES),
            "excluded_project_urls": sorted(set(pool.get("excluded_project_urls", [])) | {project_url(s["project_url"]) for s in removed}),
            "excluded_image_sha256": sorted(set(pool.get("excluded_image_sha256", [])) | {
                e["sha256"] for s in result["samples"] for e in s["evidence"]
                if s["id"] not in kept or s.get(e["purpose"]) != 1
            }),
        }
    return result


def submit_feedback(root: Path, payload: dict) -> dict:
    root = root.resolve()
    pool = read_json(root / POOL)
    errors = validate_pool(pool, root)
    if errors:
        raise ValueError("; ".join(errors))
    if pool["status"] != "PENDING_RATING":
        raise ValueError("current pool is not awaiting feedback")
    if not (root / PENDING).is_file() or (root / POOL).read_bytes() != (root / PENDING).read_bytes():
        raise ValueError("pending reference snapshot is missing or changed")
    if payload.get("reference_pool_sha256") != digest(root / PENDING):
        raise ValueError("stale reference pool hash")
    result = _feedback_result(pool, payload)
    write_json(root / POOL, result)
    return result


def submit_chat_feedback(root: Path, action: str, user_message: str, ratings=None) -> dict:
    """Apply an explicit current-turn choice without asking for a second click.

    The controller supplies only ids/axes actually named in the user's message;
    this helper does not infer preferences or parse ambiguous natural language.
    """
    if not isinstance(user_message, str) or not user_message.strip():
        raise ValueError("native chat feedback needs the explicit user message")
    pool = read_json(root / POOL)
    if pool.get("status") != "PENDING_RATING":
        raise ValueError("native chat feedback must target the currently displayed pending batch")
    if not (root / PENDING).is_file():
        raise ValueError("pending reference snapshot is missing")
    payload = dict(rater_contract_version=2, reference_pool_sha256=digest(root / PENDING), round=pool["round"],
                   interaction_mode="NATIVE_CHAT_FEEDBACK", user_message=user_message, action=action,
                   ratings=[] if ratings is None else ratings)
    return submit_feedback(root, payload)


def _verify_submission(root: Path, pool: dict) -> list[str]:
    try:
        pending = read_json(root / PENDING)
        submission = pool.get("rating_submission", {})
        if submission.get("reference_pool_sha256") != digest(root / PENDING):
            raise ValueError("rating submission hash mismatch")
        if _feedback_result(pending, submission) != pool:
            raise ValueError("pool differs from its actual rating submission")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return [str(exc)]
    return []


def replace_candidates(root: Path, candidates: list[dict]) -> dict:
    pool = read_json(root / POOL)
    initial = pool.get("status") == "PENDING_RATING" and pool.get("samples") == []
    if not initial and pool.get("status") != "RESEARCH_REQUIRED":
        raise ValueError("replacement requires a new pool or a search-again request")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("provide new candidates from actual search")
    if not initial:
        errors = validate_pool(pool, root) + _verify_submission(root, pool)
        if errors:
            raise ValueError("; ".join(errors))
    request = pool.get("research_request", {})
    kept = [_positive_projection(s) for s in pool["samples"] if s["id"] in request.get("preserve_sample_ids", [])]
    added = copy.deepcopy(candidates)
    for sample in added:
        if not isinstance(sample, dict):
            raise ValueError("candidate must be an object")
        if project_url(sample.get("project_url")) in request.get("excluded_project_urls", []):
            raise ValueError("rejected project cannot be presented again in this run")
        if any(e.get("sha256") in request.get("excluded_image_sha256", []) for e in sample.get("evidence", []) if isinstance(e, dict)):
            raise ValueError("rejected image cannot be renamed and presented again")
        sample["visual"] = sample["layout"] = None
    result = {"version": 2, "run_identity": pool["run_identity"], "round": pool["round"] + (0 if initial else 1), "status": "PENDING_RATING", "samples": kept + added,
              "excluded_project_urls": request.get("excluded_project_urls", []), "excluded_image_sha256": request.get("excluded_image_sha256", [])}
    # Validate images and schema before any canonical mutation. The preceding
    # round is archived below; carry authenticity was checked on the source pool.
    validation_copy = copy.deepcopy(result)
    validation_copy["status"] = "RESEARCH_REQUIRED"
    errors = validate_pool(validation_copy, root)
    if errors:
        raise ValueError("; ".join(errors))
    if not initial:
        archive = root / "reference-rounds" / f"round-{pool['round']}"
        write_json(archive / POOL, pool)
        archive.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / PENDING, archive / PENDING)
    write_json(root / POOL, result)
    shutil.copyfile(root / POOL, root / PENDING)
    return result


def validate_bundle(reference_pool_paths, preference_profile_paths, run_identity, root=None) -> dict:
    pool_path = next((Path(p) for p in reference_pool_paths if Path(p).is_file()), None)
    profile_path = next((Path(p) for p in preference_profile_paths if Path(p).is_file()), None)
    result = dict(valid=False, pool_path=pool_path, profile_path=profile_path, errors=[], pool_data=None, profile_data=None,
                  rated_sample_ids=[], pairwise_required=False, pairwise_generation_allowed=False)
    errors = result["errors"]
    try:
        if pool_path is None:
            raise ValueError("visual_reference_pool.json is required")
        validation_root = Path(root).resolve() if root else pool_path.parent.resolve()
        pool = result["pool_data"] = read_json(pool_path)
        errors.extend(validate_pool(pool, validation_root))
        if pool.get("run_identity") != run_identity:
            errors.append("reference pool run_identity mismatch")
        if pool.get("status") != "RATED":
            errors.append("reference search/ratings are pending; do not generate images")
        else:
            errors.extend(_verify_submission(validation_root, pool))
        samples = pool.get("samples", [])
        if not isinstance(samples, list) or not all(isinstance(s, dict) for s in samples):
            samples = []
        result["rated_sample_ids"] = [s.get("id") for s in samples if all(s.get(a) is not None for a in s.get("purposes", []))]
        if profile_path is None:
            raise ValueError("visual_preference_profile.json is required")
        profile = result["profile_data"] = read_json(profile_path)
        if profile.get("version") not in {1, 2} or profile.get("status") != "APPROVED":
            errors.append("preference profile must be APPROVED")
        if profile.get("run_identity") != run_identity:
            errors.append("preference profile run_identity mismatch")
        if profile.get("reference_pool_sha256") != digest(pool_path):
            errors.append("preference profile reference_pool_sha256 hash mismatch")
        recipe = profile.get("hybrid_recipe", {})
        if not isinstance(recipe, dict):
            recipe = {}
        if not _strings(recipe.get("rules"), nonempty=True):
            errors.append("profile needs executable hybrid rules")
        any_negative = False
        for axis in AXES:
            positives = {s.get("id") for s in samples if s.get(axis) == 1}
            negatives = {s.get("id") for s in samples if s.get(axis) == -1}
            any_negative = any_negative or bool(negatives)
            anchors = recipe.get(f"{axis}_anchor_sample_ids")
            if not isinstance(anchors, list) or not anchors or any(not isinstance(a, str) or a not in positives for a in anchors):
                errors.append(f"{axis} anchors need positive ratings; otherwise search again")
            system = profile.get(f"{axis}_system", {})
            if not isinstance(system, dict) or not _strings(system.get("keep"), nonempty=True):
                errors.append(f"{axis}_system.keep must be executable rules")
                system = {} if not isinstance(system, dict) else system
            exclusions = system.get("exclude")
            if not _strings(exclusions) or bool(exclusions) != bool(negatives):
                errors.append(f"{axis}_system.exclude must match negative evidence")
        if not _strings(profile.get("rejected_patterns")) or bool(profile.get("rejected_patterns")) != any_negative:
            errors.append("rejected_patterns must match negative evidence")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    result["valid"] = not errors
    return result


def _strings(value, nonempty=False):
    return isinstance(value, list) and (not nonempty or bool(value)) and all(isinstance(s, str) and s.strip() for s in value)


def _library(root: Path) -> dict:
    path = root / "library.json"
    value = read_json(path) if path.is_file() else {"version": 1, "entries": []}
    if value.get("version") != 1 or not isinstance(value.get("entries"), list):
        raise ValueError("invalid favorites library")
    return value


def _owned_target(root: Path, relative: str) -> Path:
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("asset destination escapes its project/library")
    return target


def add_favorites(root: Path, library_root: Path) -> dict:
    root, library_root = root.resolve(), library_root.expanduser().resolve()
    pool = read_json(root / POOL)
    if pool.get("status") not in {"RATED", "RESEARCH_REQUIRED"}:
        raise ValueError("favorites need submitted user ratings")
    errors = validate_pool(pool, root) + _verify_submission(root, pool)
    if errors:
        raise ValueError("; ".join(errors))
    library = _library(library_root)
    for sample in pool["samples"]:
        axes = [a for a in sample["purposes"] if sample.get(a) == 1]
        # An explicit whole-batch rejection overrides earlier clicks in that batch.
        if not axes or pool.get("rating_submission", {}).get("action") == "RESEARCH_ALL":
            continue
        selected = [e for e in sample["evidence"] if e["purpose"] in axes]
        identity = hashlib.sha256((project_url(sample["project_url"]) + "|" + "|".join(sorted(e["sha256"] for e in selected))).encode()).hexdigest()[:20]
        entry = {"id": identity, "project": sample["project"], "project_url": project_url(sample["project_url"]),
                 "purposes": axes, "tags": sample.get("tags", []), "evidence": [], "approval": {"run_identity": pool["run_identity"], "sample_id": sample["id"], "pool_sha256": digest(root / POOL)}}
        for evidence in selected:
            source = asset_path(root, evidence["path"])
            target = _owned_target(library_root, "assets/" + evidence["sha256"] + source.suffix.lower())
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)
            entry["evidence"].append(dict(path=target.relative_to(library_root).as_posix(), sha256=evidence["sha256"], purpose=evidence["purpose"]))
        evidence_dir = _owned_target(library_root, "approvals/" + entry["approval"]["pool_sha256"])
        evidence_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / POOL, evidence_dir / POOL)
        shutil.copyfile(root / PENDING, evidence_dir / PENDING)
        library["entries"] = [e for e in library["entries"] if e.get("id") != identity] + [entry]
    write_json(library_root / "library.json", library)
    return library


def find_favorites(library_root: Path, query: str, purpose: str, project_root: Path) -> list[dict]:
    library_root, project_root = library_root.expanduser().resolve(), project_root.resolve()
    if purpose not in AXES:
        raise ValueError("purpose must be visual or layout")
    terms = [t for t in re.split(r"\s+", query.lower().strip()) if t]
    ranked = []
    for entry in _library(library_root)["entries"]:
        if not isinstance(entry, dict) or purpose not in entry.get("purposes", []):
            continue
        searchable = " ".join([str(entry.get("project", "")), *map(str, entry.get("tags", []))]).lower()
        score = sum(t in searchable for t in terms)
        if terms and not score:
            continue
        approval = entry.get("approval", {})
        sha = approval.get("pool_sha256", "")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            continue
        evidence_dir = library_root / "approvals" / sha
        try:
            approved_pool = read_json(evidence_dir / POOL)
            if digest(evidence_dir / POOL) != sha or _verify_submission(evidence_dir, approved_pool):
                continue
            sample = next(s for s in approved_pool["samples"] if s["id"] == approval.get("sample_id"))
            if sample.get(purpose) != 1 or approved_pool.get("rating_submission", {}).get("action") == "RESEARCH_ALL":
                continue
            if project_url(sample["project_url"]) != project_url(entry["project_url"]):
                continue
            candidate = dict(id="LIB_" + entry["id"], project=entry["project"], project_url=entry["project_url"], purposes=[purpose],
                             tags=entry.get("tags", []), evidence=[], visual=None, layout=None, discovery_origin="CURATED_LIBRARY")
            for evidence in entry["evidence"]:
                if evidence["purpose"] != purpose:
                    continue
                if not any(e["purpose"] == purpose and e["sha256"] == evidence["sha256"] for e in sample["evidence"]):
                    raise ValueError("library asset was not positively rated")
                source = asset_path(library_root, evidence["path"])
                if digest(source) != evidence["sha256"]:
                    raise ValueError("library asset hash mismatch")
                check_image(source)
                target = _owned_target(project_root, "design-references/library/" + evidence["sha256"] + source.suffix.lower())
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.resolve() != source.resolve():
                    shutil.copyfile(source, target)
                candidate["evidence"].append(dict(path=target.relative_to(project_root).as_posix(), sha256=evidence["sha256"], purpose=purpose))
            if candidate["evidence"]:
                ranked.append((score, candidate))
        except (ValueError, OSError, KeyError, TypeError, StopIteration):
            continue
    unique = {}
    for _, candidate in sorted(ranked, key=lambda item: (-item[0], item[1]["id"])):
        unique.setdefault(project_url(candidate["project_url"]), candidate)
    return list(unique.values())[:8]


def initialize(root: Path) -> dict:
    if (root / POOL).exists():
        return read_json(root / POOL)
    active = read_json(root / "active_run.json")
    identity = active.get("run_identity")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("initialize the stable active run first")
    pool = dict(version=2, run_identity=identity, round=1, status="PENDING_RATING", samples=[])
    write_json(root / POOL, pool)
    return pool


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "submit", "chat-submit", "replace", "favorites-add", "favorites-find"])
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--library-root", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--query", default="")
    parser.add_argument("--purpose", choices=AXES)
    parser.add_argument("--action", choices=["CONTINUE", "RESEARCH_ALL", "RESEARCH_REJECTED"])
    parser.add_argument("--user-message")
    parser.add_argument("--ratings", type=Path)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    library = args.library_root.expanduser().resolve()
    try:
        if args.command == "init":
            result = initialize(root)
        elif args.command == "submit":
            if args.payload is None:
                raise ValueError("--payload is required")
            result = submit_feedback(root, read_json(args.payload))
        elif args.command == "chat-submit":
            ratings = json.loads(args.ratings.read_text(encoding="utf-8")) if args.ratings else None
            result = submit_chat_feedback(root, args.action, args.user_message, ratings)
        elif args.command == "replace":
            if args.candidates is None:
                raise ValueError("--candidates is required")
            data = json.loads(args.candidates.read_text(encoding="utf-8"))
            result = replace_candidates(root, data.get("samples", []) if isinstance(data, dict) else data)
        elif args.command == "favorites-add":
            result = add_favorites(root, library)
        else:
            result = find_favorites(library, args.query, args.purpose, root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
