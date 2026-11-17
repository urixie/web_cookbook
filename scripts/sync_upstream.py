"""按提交 SHA 导入 HowToCook，保留原始 Git 文件字节。"""

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from tarfile import open as tar_open

from validate_content import ROOT, SHA, inventory, stats

URL = "https://github.com/Anduin2017/HowToCook"
BRANCH = "master"
PATHS = ("README.md", "LICENSE", "dishes", "tips")


def git(*args):
    return subprocess.check_output(["git", *map(str, args)])


def latest():
    sha = git("ls-remote", URL + ".git", f"refs/heads/{BRANCH}").decode().split()[0]
    if not SHA.fullmatch(sha):
        raise ValueError("上游没有返回完整 SHA")
    return sha


def extract(repo, sha, staging):
    git_files = {}
    for entry in git("-C", repo, "ls-tree", "-rz", sha, "--", *PATHS).split(b"\0"):
        if not entry:
            continue
        flags, name = entry.decode().split("\t", 1)
        mode, kind, oid = flags.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"不支持的上游 Git 对象：{name}")
        git_files[name] = oid
    with tempfile.TemporaryFile() as archive:
        subprocess.run(["git", "-C", str(repo), "archive", sha, *PATHS], stdout=archive, check=True)
        archive.seek(0)
        with tar_open(fileobj=archive) as source:
            for member in source:
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts or "\\" in member.name:
                    raise ValueError(f"不安全的归档路径：{member.name}")
                if member.isdir():
                    continue
                if not member.isfile() or member.name not in git_files:
                    raise ValueError(f"不支持的归档路径：{member.name}")
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as content, target.open("xb") as output:
                    shutil.copyfileobj(content, output)
                if git("hash-object", "--no-filters", target).decode().strip() != git_files[member.name]:
                    raise ValueError(f"文件字节和上游 Git 对象不一致：{member.name}")
    incoming = inventory(staging)
    if incoming.keys() != git_files.keys():
        raise ValueError("导入的文件与上游 Git 树不一致")
    return incoming


def sync(source, sha, preview):
    current = ROOT / "upstream"
    lock_path = ROOT / "upstream-lock.json"
    with tempfile.TemporaryDirectory(prefix="cookbook-", dir=ROOT) as temp:
        work = Path(temp)
        if source is None:
            source = work / "source"
            git("init", "-q", source)
            for attempt in range(3):
                try:
                    git("-C", source, "fetch", "--depth=1", URL + ".git", sha)
                    break
                except subprocess.CalledProcessError:
                    if attempt == 2:
                        raise
        if git("-C", source, "rev-parse", sha + "^{commit}").decode().strip() != sha:
            raise ValueError("上游工作区缺少指定提交")
        staging = work / "content"
        staging.mkdir()
        new = extract(source, sha, staging)
        old = inventory(current)
        summary = stats(new)
        categories = json.loads((ROOT / "metadata/categories.json").read_text(encoding="utf-8"))
        if set(categories) != {*summary.get("categories", {}), "tips"} or not summary.get("tips"):
            raise ValueError("上游分类已变化，请先核对 metadata/categories.json")
        diff = {
            "added": sorted(new.keys() - old.keys()),
            "removed": sorted(old.keys() - new.keys()),
            "changed": sorted(name for name in old.keys() & new.keys() if old[name] != new[name]),
        }
        print(json.dumps({"sha": sha, "stats": summary, **diff}, ensure_ascii=False, indent=2))
        if preview:
            return
        if old == new and lock_path.is_file():
            if json.loads(lock_path.read_text(encoding="utf-8"))["sha"] == sha:
                return
        lock = {
            "url": URL, "branch": BRANCH, "sha": sha,
            "importedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stats": summary, "files": new,
        }
        staged_lock = work / "lock.json"
        staged_lock.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        backup = work / "previous"
        if current.exists():
            current.rename(backup)
        try:
            staging.rename(current)
            staged_lock.replace(lock_path)
        except OSError:
            if current.exists():
                shutil.rmtree(current)
            if backup.exists():
                backup.rename(current)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", type=lambda x: x.lower())
    parser.add_argument("--source", type=Path, help="已有的 HowToCook Git 检出目录")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    sha = args.sha or latest()
    if not SHA.fullmatch(sha):
        parser.error("--sha 必须是完整的 40 位 Git 提交 SHA")
    sync(args.source, sha, args.preview)


if __name__ == "__main__":
    main()
