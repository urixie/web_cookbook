"""核对上游原始文件清单、字节哈希和跨平台路径。"""

import json
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from unicodedata import normalize

ROOT = Path(__file__).resolve().parents[1]
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}
SHA = re.compile(r"[0-9a-f]{40}")
WINDOWS_RESERVED = re.compile(r"(?i:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])")


def inventory(source):
    paths = sorted(source.rglob("*"))
    seen = set()
    files = {}
    for path in paths:
        name = path.relative_to(source).as_posix()
        key = normalize("NFC", name).casefold()
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)() or key in seen:
            raise ValueError(f"链接或路径冲突：{name}")
        seen.add(key)
        if len(name) > 240 or any(
            part.startswith(".") or part.endswith((".", " "))
            or WINDOWS_RESERVED.fullmatch(part.split(".")[0])
            or re.search(r'[<>:"\\|?*\x00-\x1f]', part)
            for part in path.relative_to(source).parts
        ):
            raise ValueError(f"路径不能安全移植到 Windows：{name}")
        if path.is_file():
            files[name] = sha256(path.read_bytes()).hexdigest()
        elif not path.is_dir():
            raise ValueError(f"不支持的文件类型：{name}")
    return files


def stats(files):
    counts = Counter()
    categories = Counter()
    for name in files:
        path = Path(name)
        counts["files"] += 1
        if path.suffix.lower() in IMAGE_TYPES:
            counts["images"] += 1
        if path.suffix.lower() == ".md":
            if path.parts[0] == "tips":
                counts["tips"] += 1
            elif path.parts[0] == "dishes":
                if path.parts[1] == "template":
                    counts["templates"] += 1
                else:
                    counts["recipes"] += 1
                    categories[path.parts[1]] += 1
    return dict(counts, categories=dict(sorted(categories.items())))


def validate(root=ROOT):
    lock = json.loads((root / "upstream-lock.json").read_text(encoding="utf-8"))
    if (not SHA.fullmatch(lock["sha"]) or lock["branch"] != "master"
            or lock["url"] != "https://github.com/Anduin2017/HowToCook"):
        raise ValueError("上游版本锁定记录无效")
    actual = inventory(root / "upstream")
    expected = lock["files"]
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = sorted(name for name in actual.keys() & expected.keys() if actual[name] != expected[name])
    if missing or extra or changed:
        raise ValueError(f"原始内容不一致。缺少 {missing}，新增 {extra}，字节变化 {changed}")
    summary = stats(actual)
    categories = json.loads((root / "metadata/categories.json").read_text(encoding="utf-8"))
    if summary != lock["stats"] or set(categories) != {*summary["categories"], "tips"}:
        raise ValueError("分类或数量与锁定记录不一致")
    if not {"README.md", "LICENSE"} <= actual.keys() or not all(summary.get(k) for k in ("recipes", "tips", "images")):
        raise ValueError("原始内容不完整")
    license_text = (root / "upstream/LICENSE").read_text(encoding="utf-8")
    if "free and unencumbered software released into the public domain" not in license_text:
        raise ValueError("上游许可证已变化，请先核实授权")
    print(json.dumps({"sha": lock["sha"], **summary}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    validate()
