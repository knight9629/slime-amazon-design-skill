#!/usr/bin/env python3
"""Verify the complete release using only Python's standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys


EXPECTED_SKILLS = (
    "amazon-ai-design-workflow-orchestrator",
    "amazon-image-production-runner",
    "product-reference-composer",
    "amazon-competitor-creative-research",
    "amazon-product-selling-point-brief",
    "amazon-creative-style-sampler",
)
ROOT_FILES = ("README.md", "RELEASE_NOTES.md", "install.py", "verify_package.py", "requirements.txt")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("不安全的清单路径：" + repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("", ".", "..") for p in value.split("/")):
        raise ValueError("不安全的清单路径：" + repr(value))
    return path


def verify_package(root):
    root = Path(root).resolve()
    # Release payloads contain ordinary files only. User-created virtualenv/Git
    # metadata at the root are not installed and may have their own links.
    for folder, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            candidate = Path(folder) / name
            if candidate.is_symlink():
                raise ValueError("安装包包含符号链接，请重新下载完整 ZIP：" + str(candidate.relative_to(root)))
        if Path(folder) == root:
            directories[:] = [name for name in directories if name not in (".git", ".venv", "__pycache__")]
    manifest_path = root / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("package") != "complete":
        raise ValueError("清单不是完整安装包（package 应为 complete）。")
    skills = manifest.get("skills")
    if not isinstance(skills, list) or sorted(skills) != sorted(EXPECTED_SKILLS):
        raise ValueError("清单必须包含且只包含 6 个指定 Skill。")
    if not isinstance(manifest.get("version"), str) or not isinstance(manifest.get("workflow_version"), str):
        raise ValueError("清单缺少 version / workflow_version。")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("清单缺少文件哈希列表。")
    listed = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("清单文件记录格式错误。")
        relative = safe_relative_path(record.get("path"))
        name = relative.as_posix()
        if name in listed or name == "MANIFEST.json":
            raise ValueError("清单路径重复或包含清单自身：" + name)
        listed.add(name)
        expected_hash = record.get("sha256")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("SHA256 格式错误：" + name)
        source = root.joinpath(*relative.parts)
        component = root
        for part in relative.parts:
            component = component / part
            if component.is_symlink():
                raise ValueError("清单文件路径包含符号链接：" + name)
        if not source.is_file() or sha256(source) != expected_hash:
            raise ValueError("文件缺失或 SHA256 不一致：" + name)
    required = set(ROOT_FILES) | {"skills/" + name + "/SKILL.md" for name in EXPECTED_SKILLS}
    if not required.issubset(listed):
        raise ValueError("清单缺少必需文件：" + ", ".join(sorted(required - listed)))
    skills_root = root / "skills"
    if not skills_root.is_dir() or sorted(p.name for p in skills_root.iterdir()) != sorted(EXPECTED_SKILLS):
        raise ValueError("skills 目录必须完整包含 6 个指定 Skill。")
    for path in skills_root.rglob("*"):
        if path.is_file() and path.relative_to(root).as_posix() not in listed:
            raise ValueError("Skill 中有未登记的文件：" + str(path.relative_to(root)))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="校验完整安装包的 6 个 Skill 和所有清单哈希。")
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    try:
        manifest = verify_package(args.package)
    except (OSError, ValueError, TypeError) as error:
        print("安装包校验失败：" + str(error), file=sys.stderr)
        return 1
    print("安装包文件完整：6 个 Skill，{} 个文件，发行版本 {}。".format(len(manifest["files"]), manifest["version"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
