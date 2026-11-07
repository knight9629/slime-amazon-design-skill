#!/usr/bin/env python3
"""Install the six verified skills; never download or install dependencies."""
import argparse
from datetime import datetime
import importlib
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
from verify_package import EXPECTED_SKILLS, OS_GENERATED_NAMES, sha256, verify_package


def check_environment():
    ready = sys.version_info >= (3, 10)
    print("Python {}：{}（需要 3.10 或以上）".format(sys.version.split()[0], "就绪" if ready else "未就绪"))
    for module, label in (("PIL", "Pillow"),):
        try:
            imported = importlib.import_module(module)
            print(label + "：就绪 " + str(getattr(imported, "__version__", "")))
        except Exception:
            ready = False
            print(label + "：未就绪（未安装或无法导入）")
    if not ready:
        print("运行环境未就绪。请使用 Python 3.10+，并在该 Python 环境执行：python3 -m pip install -r requirements.txt")
    print("浏览、生图及真实图片引用能力仍需在 Codex 中检查；本检查不代表已完成生图或设计验收。")
    return ready


def verify_installed(dest, manifest):
    for record in manifest["files"]:
        if record["path"].startswith("skills/"):
            path = dest / record["path"][len("skills/"):]
            if not path.is_file() or path.is_symlink() or sha256(path) != record["sha256"]:
                raise ValueError("安装后回读校验失败：" + str(path))
    for name in EXPECTED_SKILLS:
        if not (dest / name / "SKILL.md").is_file():
            raise ValueError("安装后缺少 Skill：" + name)


def install(root, dest, manifest, backup):
    root = root.resolve()
    dest = dest.expanduser().resolve()
    if root == dest or root in dest.parents or dest in root.parents:
        raise ValueError("安装目录不能与安装包目录重叠。请选择独立的 skills 目录。")
    if dest.exists() and not dest.is_dir():
        raise ValueError("安装目标不是目录：" + str(dest))
    conflicts = [name for name in EXPECTED_SKILLS if os.path.lexists(dest / name)]
    if conflicts and not backup:
        raise ValueError("已存在同名 Skill：{}。保留现状；如需备份后更新，请加 --backup。".format(", ".join(conflicts)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = None
    moved = []
    installed = []
    with tempfile.TemporaryDirectory(prefix=".slime-install-", dir=dest.parent) as temporary:
        stage = Path(temporary)
        skip_generated = shutil.ignore_patterns(*OS_GENERATED_NAMES, "._*", "__pycache__", "*.pyc")
        for name in EXPECTED_SKILLS:
            shutil.copytree(root / "skills" / name, stage / name, ignore=skip_generated)
        verify_installed(stage, manifest)
        if conflicts:
            backup_root = dest.parent / (dest.name + "-backups")
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_dir = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=backup_root))
        dest.mkdir(exist_ok=True)
        try:
            for name in EXPECTED_SKILLS:
                target = dest / name
                if os.path.lexists(target):
                    # Recheck after staging so a newly created local skill is not
                    # overwritten without the requested backup policy.
                    if not backup or backup_dir is None:
                        raise ValueError("安装期间出现同名 Skill，已停止：" + name)
                    target.rename(backup_dir / name)
                    moved.append(name)
                (stage / name).rename(target)
                installed.append(name)
            verify_installed(dest, manifest)
        except Exception:
            for name in reversed(installed):
                shutil.rmtree(dest / name)
            for name in reversed(moved):
                (backup_dir / name).rename(dest / name)
            raise
    print("文件安装完成并已回读校验：6 个 Skill → " + str(dest))
    if backup_dir:
        print("原有 Skill 已备份（保留原符号链接）：" + str(backup_dir))


def main():
    parser = argparse.ArgumentParser(description="安装史莱姆亚马逊设计 Skill 完整包。")
    parser.add_argument("--check", action="store_true", help="只检查包和运行环境，不写入安装目录")
    default_home = Path(os.environ.get("CODEX_HOME") or str(Path.home() / ".codex"))
    parser.add_argument("--dest", type=Path, default=default_home / "skills", help="指定 Skill 安装目录")
    parser.add_argument("--backup", action="store_true", help="将同名 Skill 移到目录外备份后更新")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        manifest = verify_package(root)
        print("安装包文件完整：6 个 Skill，发行版本 " + manifest["version"] + "。")
        print("Codex 技能目录：" + str(args.dest.expanduser().resolve()))
        ready = check_environment()
        if args.check:
            return 0 if ready else 2
        install(root, args.dest, manifest, args.backup)
        if not ready:
            print("文件已安装；运行环境尚未就绪，请按上方提示补齐后重新执行 --check。")
        print("请重新打开 Codex 或新建对话，让新安装的 Skills 被识别。")
        return 0
    except (OSError, ValueError, TypeError) as error:
        print("安装失败：" + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
