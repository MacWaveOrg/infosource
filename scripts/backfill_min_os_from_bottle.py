#!/usr/bin/env python3

# backfill_min_os_from_bottle.py
#
# 从 Bottle 仓库的产物里提取 minos，回填到索引的 `min_os` 字段。
#
# 与 backfill_min_os.py 的分工：那个从**本机已安装**的树里取，只能覆盖装过的包；
# 这个直接从 Bottle 下载每个版本的产物，覆盖全库（两架构）。产物不必能运行，
# otool 只读 Mach-O 头，所以 amd64 的包在 arm64 机器上一样能分析。
#
# 提取规则与那个脚本一致：一个产物里所有 Mach-O 的 LC_BUILD_VERSION 取最大值。
# 例：tmux@3.6 本体 12.0，它带的 libevent dylib 是 12.1，所以整包是 12.1。
#
# 用法：
#   python3 scripts/backfill_min_os_from_bottle.py --dry-run
#   python3 scripts/backfill_min_os_from_bottle.py
#   python3 scripts/backfill_min_os_from_bottle.py --only jq --only tmux
#   python3 scripts/backfill_min_os_from_bottle.py --arch amd64 --refresh
#
# 幂等：记录里已有 min_os 的默认跳过；要重算用 --refresh。

import argparse
import bz2
import gzip
import io
import lzma
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ARCHIVE_RE = re.compile(r'^(?P<name>[^@]+)@(?P<ver>.+?)\.(?P<arch>arm64|amd64)(?P<ext>\..+)?$')
MIN_OS_RE = re.compile(r'^min_os:[ \t]*"([^"]*)"[ \t]*$', re.MULTILINE)

# Mach-O 头。先按 magic 过滤，再调 otool —— 归档里成百个文件时这一步省很多时间。
MACHO_MAGICS = (
    b"\xcf\xfa\xed\xfe",   # MH_MAGIC_64
    b"\xce\xfa\xed\xfe",   # MH_MAGIC
    b"\xca\xfe\xba\xbe",   # FAT（大端）
    b"\xbe\xba\xfe\xca",   # FAT（小端）
)


def parse_dotted(text):
    """把 "12.1" / "10.15.7" 解析成可比较的整数元组，不合法返回 None。"""
    parts = text.strip().split(".")
    if not 1 <= len(parts) <= 3:
        return None
    if not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def macho_minos(path):
    """单个文件的 minos；不是 Mach-O 或读不到时返回 None。"""
    try:
        with open(path, "rb") as handle:
            if handle.read(4) not in MACHO_MAGICS:
                return None
    except OSError:
        return None

    try:
        done = subprocess.run(["otool", "-l", str(path)],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None

    # 两种写法都要认：
    #   LC_BUILD_VERSION      → minos 10.13      （较新的工具链）
    #   LC_VERSION_MIN_MACOSX → version 10.13    （老的，btop@1.4.5 这类）
    # 只认前者的话，一批老产物的 min_os 会全部提取不到。
    lines = done.stdout.splitlines()
    for index, line in enumerate(lines):
        command = line.strip()
        if command == "cmd LC_BUILD_VERSION":
            for following in lines[index:index + 8]:
                field = following.strip()
                if field.startswith("minos "):
                    return field.split()[1]
        elif command == "cmd LC_VERSION_MIN_MACOSX":
            for following in lines[index:index + 8]:
                field = following.strip()
                if field.startswith("version "):
                    return field.split()[1]
    return None


def merge(found, path):
    """把 path 的 minos 并进 (value, tuple)，返回新的一对。"""
    value = macho_minos(path)
    if not value:
        return found
    parsed = parse_dotted(value)
    if parsed is None:
        return found
    best_value, best_tuple = found
    if best_tuple is None or parsed > best_tuple:
        return value, parsed
    return found


def tree_max_minos(root):
    """整棵目录里所有 Mach-O 的 minos 最大值。"""
    found = (None, None)
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            candidate = Path(dirpath) / name
            if candidate.is_symlink() or not candidate.is_file():
                continue
            found = merge(found, candidate)
    return found[0]


def conda_members(data):
    """.conda 是 zip，主体在 pkg-*.tar.bz2（新格式是 pkg-*.tar.zst）里。"""
    try:
        outer = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return []

    blobs = []
    for info in outer.infolist():
        name = info.filename
        if name.startswith("pkg-") and name.endswith(".tar.bz2"):
            blobs.append(outer.read(name))
            continue
        if name.startswith("pkg-") and name.endswith(".tar.zst"):
            try:
                from compression import zstd          # Python 3.14+
            except ImportError:
                print(f"    {name}: 需要 compression.zstd（Python 3.14+），跳过")
                continue
            blobs.append(zstd.decompress(outer.read(name)))
    return blobs


def extract_max_minos(payload_path):
    """从一个产物文件里取 max minos，自动处理裸文件与各种归档。"""
    with tempfile.TemporaryDirectory() as work:
        work_path = Path(work)
        data = payload_path.read_bytes()

        # 裸 Mach-O
        if data[:4] in MACHO_MAGICS:
            target = work_path / "payload"
            target.write_bytes(data)
            return merge((None, None), target)[0]

        # 单文件压缩：ffmpeg@6.0.arm64.gz 是 gzip 包着一个裸二进制，不是 tar。
        # 库里这类有 7 个（3 gz / 2 bz2 / 2 xz），不认的话它们的 min_os 永远是空的。
        if data[:2] == b"\x1f\x8b":
            raw = gzip.decompress(data)
        elif data[:6] == b"\xfd7zXZ\x00":
            raw = lzma.decompress(data)
        elif data[:3] == b"BZh":
            raw = bz2.decompress(data)
        else:
            raw = None
        if raw is not None and raw[:4] in MACHO_MAGICS:
            target = work_path / "payload"
            target.write_bytes(raw)
            return merge((None, None), target)[0]

        # .conda：内层是 tar.zst，解压 zstd 之后是**裸 tar**，所以交给 tarfile
        # 自己认格式（mode 省略 = 自动侦测），不要写死 r:bz2。
        if payload_path.suffix == ".conda":
            for index, blob in enumerate(conda_members(data)):
                try:
                    with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
                        archive.extractall(work_path / f"c{index}", filter="data")
                except tarfile.TarError as error:
                    print(f"    .conda 内层解压失败: {error}")
                    continue
            return tree_max_minos(work)

        # zip：注意 zipfile.extractall 没有 filter 参数（那是 tarfile 的），
        # 路径穿越得自己挡 —— 成员名以 / 开头或含 .. 一律拒绝。
        if zipfile.is_zipfile(io.BytesIO(data)):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    root = work_path.resolve()
                    for info in archive.infolist():
                        target = (root / info.filename).resolve()
                        if target != root and root not in target.parents:
                            raise ValueError(f"成员越界: {info.filename}")
                    archive.extractall(work_path)
            except (zipfile.BadZipFile, ValueError) as error:
                print(f"    zip 解压失败: {error}")
                return None
            return tree_max_minos(work)

        # tar 家族（tarfile 自己认 gz/bz2/xz）
        try:
            with tarfile.open(payload_path) as archive:
                archive.extractall(work_path, filter="data")
        except (tarfile.TarError, OSError):
            return None
        return tree_max_minos(work)


def write_field(record_path, min_os, dry_run):
    """把 min_os 写进版本记录；已有该行则原位替换，没有则追加。"""
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


def collect_targets(index_root, arch_filter, refresh):
    """返回 {包名: [(版本, 架构, 记录路径), …]}，只收还需要处理的。"""
    targets = {}
    for arch in ("arm64", "amd64"):
        if arch_filter and arch != arch_filter:
            continue
        folder = index_root / f"pkginfo_{arch}"
        if not folder.is_dir():
            continue
        for record in sorted(folder.glob("*/_*@*")):
            if record.name.endswith("@common"):
                continue
            pkg, _, version = record.name[1:].partition("@")
            if not version:
                continue
            # test_* 是负向样本（缺 sha256 / sha256 不符）与格式测试样本，
            # Bottle 里没有它们的真实产物，也不需要 min_os。
            if pkg.startswith("test_"):
                continue
            if not refresh and MIN_OS_RE.search(record.read_text(encoding="utf-8")):
                continue
            targets.setdefault(pkg, []).append((version, arch, record))
    return targets


def download(pkg, repo, work_dir):
    """拉这个包的全部资产；返回资产路径列表。"""
    cmd = ["gh", "release", "download", pkg, "--repo", repo, "--dir", str(work_dir), "--clobber"]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        message = (done.stderr or done.stdout).strip().splitlines()
        return None, (message[-1] if message else f"gh exited {done.returncode}")
    return sorted(p for p in Path(work_dir).iterdir() if p.is_file()), None


def main():
    ap = argparse.ArgumentParser(description="从 Bottle 产物回填索引的 min_os")
    ap.add_argument("--repo", default="MacWaveOrg/Bottle", help="产物所在的 GitHub 仓库")
    ap.add_argument("--index-root", default=str(REPO_ROOT / "pkg"), help="索引根目录（含 pkginfo_*）")
    ap.add_argument("--only", action="append", default=None, help="只处理这些包（可重复）")
    ap.add_argument("--arch", choices=["arm64", "amd64"], default=None)
    ap.add_argument("--refresh", action="store_true", help="已有 min_os 的也重算")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cache", default=None,
                    help="下载缓存目录；已有资产的包不再重复下载（跨次运行复用）")
    args = ap.parse_args()

    if not shutil.which("gh"):
        print("找不到 gh（GitHub CLI），无法下载产物", file=sys.stderr)
        return 2

    index_root = Path(args.index_root)
    targets = collect_targets(index_root, args.arch, args.refresh)
    if args.only:
        wanted = set(args.only)
        targets = {pkg: items for pkg, items in targets.items() if pkg in wanted}
    if not targets:
        print("没有需要回填的记录", file=sys.stderr)
        return 1

    counts = {"added": 0, "updated": 0, "unchanged": 0, "missing": 0, "no-minos": 0}
    print(f"包 {len(targets)} 个，记录 {sum(len(v) for v in targets.values())} 条"
          + ("  [dry-run]" if args.dry_run else ""))
    print()

    cache_root = Path(args.cache) if args.cache else None
    if cache_root:
        cache_root.mkdir(parents=True, exist_ok=True)

    for pkg in sorted(targets):
        items = targets[pkg]
        with tempfile.TemporaryDirectory() as scratch:
            work = Path(scratch)
            if cache_root:
                work = cache_root / pkg
                work.mkdir(parents=True, exist_ok=True)

            cached = [p for p in work.iterdir() if p.is_file()] if cache_root else []
            if cached:
                assets, error = sorted(cached), None
                print(f"  {pkg}: 用缓存 {len(assets)} 个资产")
            else:
                assets, error = download(pkg, args.repo, work)
            if assets is None:
                print(f"  {pkg}: 下载失败 —— {error}")
                counts["missing"] += len(items)
                continue

            by_key = {}
            for asset in assets:
                match = ARCHIVE_RE.match(asset.name)
                if not match:
                    continue
                by_key[(match["ver"], match["arch"])] = asset

            for version, arch, record in items:
                asset = by_key.get((version, arch))
                if asset is None:
                    counts["missing"] += 1
                    print(f"    {pkg}@{version}.{arch}: 产物里没有这一份")
                    continue

                min_os = extract_max_minos(asset)
                if min_os is None:
                    counts["no-minos"] += 1
                    print(f"    {pkg}@{version}.{arch}: 没有 Mach-O 的 minos")
                    continue

                action = write_field(record, min_os, args.dry_run)
                counts[action] += 1
                print(f"    {pkg}@{version}.{arch}: min_os={min_os} -> {action}")

    print()
    print("  ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
