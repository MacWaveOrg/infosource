#!/usr/bin/env python3

# backfill_min_os.py
#
# 从已安装的产物里提取 LC_BUILD_VERSION 的 minos，回填到索引版本记录的
# `min_os` 字段。
#
# 为什么从产物提取：minos 是构建时写进 Mach-O 的，是权威来源，不需要人工填。
# 一个包里所有 Mach-O 的 minos 取**最大值** —— 例如 tmux@3.6 本体是 12.0，
# 但它带的 libevent dylib 是 12.1，那么整包要求就是 12.1。
#
# 注意 minos 是「构建时的最低声明」，不等于「真实 API 需求」：jq@1.8.2 声明
# 14.0，在 macOS 12.7.6 上实测照常运行。所以这个字段在客户端只用于提示，
# 不用于拦截（见 MacWave 的 pkg/pkginstaller.py:check_min_os）。
#
# 用法：
#   python3 scripts/backfill_min_os.py --dry-run     # 只看会改哪些
#   python3 scripts/backfill_min_os.py               # 写回索引
#   python3 scripts/backfill_min_os.py --arch amd64  # 指定索引目录
#   python3 scripts/backfill_min_os.py --base-dir /opt/macwave

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MIN_OS_RE = re.compile(r'^min_os:[ \t]*"([^"]*)"[ \t]*$', re.MULTILINE)


def parse_dotted(text):
    """把 "12.1" / "10.15.7" 解析成可比较的整数元组，不合法返回 None。"""
    parts = text.strip().split(".")
    if not 1 <= len(parts) <= 3:
        return None
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def macho_min_os(path):
    """返回单个文件的 minos，不是 Mach-O 或读不到时返回 None。"""
    try:
        done = subprocess.run(["otool", "-l", str(path)],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None

    lines = done.stdout.splitlines()
    for index, line in enumerate(lines):
        if "LC_BUILD_VERSION" not in line:
            continue
        for following in lines[index:index + 8]:
            stripped = following.strip()
            if stripped.startswith("minos "):
                return stripped.split()[1]
    return None


def tree_min_os(root):
    """整棵目录里所有 Mach-O 的 minos 最大值；一个都没有时返回 None。"""
    best = None
    best_tuple = None
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        found = macho_min_os(path)
        if not found:
            continue
        parsed = parse_dotted(found)
        if parsed is None:
            continue
        if best_tuple is None or parsed > best_tuple:
            best, best_tuple = found, parsed
    return best


def installed_packages(base_dir):
    """列出 (包名, 版本, 目录)，只取 bin/<名>@<版>/ 这一层。"""
    bin_dir = base_dir / "bin"
    if not bin_dir.is_dir():
        return []
    found = []
    for entry in sorted(bin_dir.iterdir()):
        if not entry.is_dir() or "@" not in entry.name:
            continue
        name, _, version = entry.name.partition("@")
        found.append((name, version, entry))
    return found


def write_field(record_path, min_os, dry_run):
    """把 min_os 写进版本记录；已有该行则原位替换，没有则追加到末尾。"""
    record_path = Path(record_path)
    if not record_path.is_file():
        return "no-record"

    text = record_path.read_text(encoding="utf-8")
    line = f'min_os: "{min_os}"'

    if MIN_OS_RE.search(text):
        updated = MIN_OS_RE.sub(line, text, count=1)
        action = "updated"
    else:
        if not text.endswith("\n"):
            text += "\n"
        updated = text + line + "\n"
        action = "added"

    if updated == text:
        return "unchanged"
    if not dry_run:
        record_path.write_text(updated, encoding="utf-8")
    return action


def main():
    ap = argparse.ArgumentParser(description="把产物的 minos 回填到索引的 min_os 字段")
    ap.add_argument("--base-dir", default=str(Path.home() / ".local" / "macwave"),
                    help="MacWave 安装根目录（默认 ~/.local/macwave）")
    ap.add_argument("--index-dir", default=None,
                    help="索引目录（默认按 --arch 推成 pkg/pkginfo_<arch>）")
    ap.add_argument("--arch", default=None, choices=["arm64", "amd64"],
                    help="目标索引架构（默认按本机推断）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = ap.parse_args()

    arch = args.arch
    if arch is None:
        import platform
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"

    index_dir = Path(args.index_dir) if args.index_dir else REPO_ROOT / "pkg" / f"pkginfo_{arch}"
    if not index_dir.is_dir():
        print(f"index dir not found: {index_dir}", file=sys.stderr)
        return 2

    base_dir = Path(args.base_dir)
    packages = installed_packages(base_dir)
    if not packages:
        print(f"no installed packages under {base_dir}/bin", file=sys.stderr)
        return 1

    counts = {"added": 0, "updated": 0, "unchanged": 0, "no-record": 0, "no-minos": 0}
    print(f"arch={arch}  index={index_dir}  base={base_dir}"
          + ("  [dry-run]" if args.dry_run else ""))
    print()

    for name, version, target in packages:
        min_os = tree_min_os(target)
        if min_os is None:
            counts["no-minos"] += 1
            print(f"  {name}@{version}: no Mach-O with LC_BUILD_VERSION, skipped")
            continue

        record = index_dir / name / f"_{name}@{version}"
        action = write_field(record, min_os, args.dry_run)
        counts[action] += 1
        print(f"  {name}@{version}: min_os={min_os} -> {action}")

    print()
    print("  ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
