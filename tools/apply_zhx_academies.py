#!/usr/bin/env python3
"""Idempotently project the named-academy manifest into province history.

Run this as the final province-history projection after every map, polity,
culture and religion generator which can rebuild one of the twelve target
histories. The academy's unique permanent modifier remains the gameplay
authority; this tool only restores its manifest-declared 1444 location.

The entire manifest and every target history are validated before the first
write. Known academy blocks are removed with a brace-aware reader, then one
canonical block is inserted after the unique top-level ``is_city = yes`` line.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "guangdong_independent_practice"
MANIFEST = ROOT / "planning/religion_academies/academy_manifest.json"
HISTORY = MOD / "history/provinces"

SCHOOLS = ("ru", "fa", "mo", "dao", "bing", "zongheng")
REQUIRED_FIELDS = (
    "key",
    "name",
    "school",
    "province_id",
    "province_name",
    "initial_owner",
    "history_file",
    "modifier",
)
UTF8_BOM = b"\xef\xbb\xbf"
HISTORY_ID_RE = re.compile(r"^(\d+)\s*-\s*.+\.txt$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def strip_code_comment(line: str) -> str:
    """Return one Clausewitz line without a comment outside a quoted string."""

    in_string = False
    escaped = False
    for index, char in enumerate(line):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "#":
            return line[:index]
    return line


def structural_lines(text: str):
    """Yield ``(offset, depth, in_string, line)`` at each physical line start."""

    depth = 0
    in_string = False
    escaped = False
    offset = 0
    for line in text.splitlines(keepends=True):
        yield offset, depth, in_string, line
        in_comment = False
        for char in line:
            if in_comment:
                if char in "\r\n":
                    in_comment = False
                continue
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == "#":
                in_comment = True
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                require(depth >= 0, "province history has a closing brace without opener")
        offset += len(line)
    require(not in_string, "province history has an unterminated string")
    require(depth == 0, f"province history has unbalanced braces ({depth})")


def matching_close(text: str, opening: int) -> int:
    depth = 0
    in_string = False
    in_comment = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_comment:
            if char in "\r\n":
                in_comment = False
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            require(depth >= 0, "province modifier block closes without opener")
            if depth == 0:
                return index
    raise ValueError("province modifier block has no matching closing brace")


def direct_scalar_values(text: str, key: str) -> list[str]:
    """Read direct scalar assignments from one Clausewitz scope body."""

    values: list[str] = []
    pattern = re.compile(
        rf"^[ \t]*{re.escape(key)}[ \t]*=[ \t]*([^\s{{}}]+)[ \t]*$"
    )
    for _offset, depth, in_string, line in structural_lines(text):
        if depth != 0 or in_string:
            continue
        match = pattern.match(strip_code_comment(line).rstrip("\r\n"))
        if match:
            values.append(match.group(1))
    return values


def unique_top_level_scalar(text: str, key: str, filename: str) -> str:
    values = direct_scalar_values(text, key)
    require(
        len(values) == 1,
        f"{filename}: expected one top-level {key}, found {len(values)}",
    )
    return values[0]


def history_id(path: Path) -> int | None:
    match = HISTORY_ID_RE.fullmatch(path.name)
    return int(match.group(1)) if match else None


def decode_history(path: Path) -> tuple[str, bool]:
    data = path.read_bytes()
    has_bom = data.startswith(UTF8_BOM)
    payload = data[len(UTF8_BOM) :] if has_bom else data
    return payload.decode("utf-8"), has_bom


def encode_history(text: str, has_bom: bool) -> bytes:
    return (UTF8_BOM if has_bom else b"") + text.encode("utf-8")


def newline_for(text: str, filename: str) -> str:
    crlf = text.count("\r\n")
    bare_lf = text.count("\n") - crlf
    bare_cr = text.count("\r") - crlf
    styles = sum(value > 0 for value in (crlf, bare_lf, bare_cr))
    require(styles <= 1, f"{filename}: mixed newline styles are not replay-safe")
    if crlf:
        return "\r\n"
    if bare_cr:
        return "\r"
    return "\n"


def canonical_block(modifier: str, newline: str) -> str:
    return newline.join(
        (
            "add_permanent_province_modifier = {",
            f"    name = {modifier}",
            "    duration = -1",
            "}",
        )
    ) + newline


def permanent_modifier_spans(
    text: str, known_modifiers: set[str]
) -> list[tuple[int, int]]:
    """Locate all known permanent-modifier blocks, independent of field order."""

    spans: list[tuple[int, int]] = []
    block_re = re.compile(
        r"^[ \t]*add_permanent_province_modifier[ \t]*=[ \t]*\{"
    )
    for offset, _depth, in_string, line in structural_lines(text):
        if in_string:
            continue
        code = strip_code_comment(line).rstrip("\r\n")
        match = block_re.match(code)
        if not match:
            continue
        opening = offset + code.find("{", match.start())
        closing = matching_close(text, opening)
        body = text[opening + 1 : closing]
        names = direct_scalar_values(body, "name")
        if not known_modifiers.intersection(names):
            continue
        require(
            len(names) == 1 and names[0] in known_modifiers,
            "academy permanent modifier block must contain one known direct name",
        )
        end = closing + 1
        while end < len(text) and text[end] in " \t":
            end += 1
        if end < len(text) and text[end] == "#":
            while end < len(text) and text[end] not in "\r\n":
                end += 1
        if text.startswith("\r\n", end):
            end += 2
        elif end < len(text) and text[end] in "\r\n":
            end += 1
        spans.append((offset, end))
    return spans


def remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    previous_end = -1
    for start, end in sorted(spans):
        require(start >= previous_end, "academy modifier spans overlap")
        previous_end = end
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + text[end:]
    return text


def top_level_city_end(text: str, filename: str) -> int:
    pattern = re.compile(r"^[ \t]*is_city[ \t]*=[ \t]*yes[ \t]*$")
    matches: list[int] = []
    for offset, depth, in_string, line in structural_lines(text):
        if depth != 0 or in_string:
            continue
        code = strip_code_comment(line).rstrip("\r\n")
        if pattern.match(code):
            matches.append(offset + len(code))
    require(
        len(matches) == 1,
        f"{filename}: expected one top-level is_city = yes, found {len(matches)}",
    )
    return matches[0]


def validate_manifest(data: dict[str, object]) -> list[dict[str, object]]:
    require(data.get("schema_version") == 1, "unsupported academy manifest schema")
    require(data.get("campaign_start") == "1444.11.11", "campaign start drifted")
    require(
        data.get("gameplay_authority") == "unique_permanent_province_modifier",
        "academy authority drifted",
    )
    require(
        data.get("eligible_country_religion") == "confucianism",
        "academy country religion boundary drifted",
    )
    academies = data.get("academies")
    require(isinstance(academies, list), "academy manifest lacks academy list")
    require(len(academies) == 12, "academy manifest must contain twelve entries")

    unique: defaultdict[str, set[object]] = defaultdict(set)
    school_counts: Counter[str] = Counter()
    for index, academy in enumerate(academies, start=1):
        require(isinstance(academy, dict), f"academy entry {index} is not an object")
        missing = [field for field in REQUIRED_FIELDS if field not in academy]
        require(not missing, f"academy entry {index} lacks fields: {', '.join(missing)}")
        key = academy["key"]
        name = academy["name"]
        school = academy["school"]
        province_id = academy["province_id"]
        province_name = academy["province_name"]
        owner = academy["initial_owner"]
        history_file = academy["history_file"]
        modifier = academy["modifier"]
        require(
            isinstance(key, str) and re.fullmatch(r"[a-z][a-z0-9_]*", key),
            f"invalid academy key {key!r}",
        )
        require(
            isinstance(name, str) and bool(name.strip()), f"{key}: invalid academy name"
        )
        require(school in SCHOOLS, f"{key}: invalid school {school!r}")
        require(
            isinstance(province_id, int) and province_id > 0,
            f"{key}: invalid province ID",
        )
        require(
            isinstance(province_name, str) and bool(province_name.strip()),
            f"{key}: invalid province name",
        )
        require(
            isinstance(owner, str) and re.fullmatch(r"[A-Z0-9]{3}", owner),
            f"{key}: invalid owner tag",
        )
        require(
            isinstance(history_file, str) and Path(history_file).name == history_file,
            f"{key}: unsafe history filename",
        )
        require(
            history_id(Path(history_file)) == province_id,
            f"{key}: province/history filename mismatch",
        )
        require(modifier == f"zhx_academy_{key}", f"{key}: modifier/key mismatch")
        for field in ("key", "name", "province_id", "history_file", "modifier"):
            value = academy[field]
            require(value not in unique[field], f"duplicate academy {field}: {value}")
            unique[field].add(value)
        school_counts[str(school)] += 1
    require(
        school_counts == Counter({school: 2 for school in SCHOOLS}),
        f"each school must have two academies: {school_counts}",
    )
    return academies


def load_manifest() -> list[dict[str, object]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "academy manifest root must be an object")
    return validate_manifest(data)


def load_and_validate_histories(
    academies: list[dict[str, object]],
) -> tuple[dict[Path, tuple[str, bool]], set[Path]]:
    paths = sorted(HISTORY.glob("*.txt"))
    documents = {path: decode_history(path) for path in paths}
    by_id: defaultdict[int, list[Path]] = defaultdict(list)
    for path in paths:
        province_id = history_id(path)
        if province_id is not None:
            by_id[province_id].append(path)

    targets: set[Path] = set()
    for academy in academies:
        province_id = int(academy["province_id"])
        target = HISTORY / str(academy["history_file"])
        matches = by_id[province_id]
        require(
            matches == [target],
            f"province {province_id}: expected sole local history {target.name}; found "
            + (", ".join(path.name for path in matches) or "none"),
        )
        text = documents[target][0]
        owner = unique_top_level_scalar(text, "owner", target.name)
        religion = unique_top_level_scalar(text, "religion", target.name)
        require(
            owner == academy["initial_owner"],
            f"{target.name}: owner {owner}, expected {academy['initial_owner']}",
        )
        require(
            religion == "confucianism",
            f"{target.name}: religion {religion}, expected confucianism",
        )
        require(
            unique_top_level_scalar(text, "is_city", target.name) == "yes",
            f"{target.name}: academy target is not a city",
        )
        targets.add(target)
    return documents, targets


def project_documents(
    documents: dict[Path, tuple[str, bool]],
    academies: list[dict[str, object]],
    targets: set[Path],
) -> tuple[dict[Path, tuple[str, bool]], set[Path]]:
    known_modifiers = {str(academy["modifier"]) for academy in academies}
    texts = {path: text for path, (text, _bom) in documents.items()}
    affected: set[Path] = set(targets)

    for path in sorted(texts):
        spans = permanent_modifier_spans(texts[path], known_modifiers)
        if spans:
            texts[path] = remove_spans(texts[path], spans)
            affected.add(path)

    for academy in academies:
        target = HISTORY / str(academy["history_file"])
        text = texts[target]
        newline = newline_for(text, target.name)
        city_end = top_level_city_end(text, target.name)
        remainder = text[city_end:]
        remainder = re.sub(r"^(?:[ \t]*(?:\r\n|\n|\r))+", "", remainder)
        texts[target] = (
            text[:city_end]
            + newline
            + canonical_block(str(academy["modifier"]), newline)
            + newline
            + remainder
        )

    rendered = {
        path: (texts[path], documents[path][1]) for path in documents
    }
    return rendered, affected


def render_projection() -> tuple[dict[Path, bytes], set[Path]]:
    academies = load_manifest()
    documents, targets = load_and_validate_histories(academies)
    rendered, affected = project_documents(documents, academies, targets)
    rerendered, _rerendered_affected = project_documents(rendered, academies, targets)
    require(rendered == rerendered, "academy projection is not idempotent")
    encoded = {
        path: encode_history(text, has_bom)
        for path, (text, has_bom) in rendered.items()
    }
    return encoded, affected


def atomic_write(path: Path, data: bytes) -> None:
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.zhx-academy-",
            delete=False,
        ) as handle:
            temporary_name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, path.stat().st_mode)
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def run(check: bool) -> None:
    rendered, affected = render_projection()
    stale = [path for path in sorted(affected) if path.read_bytes() != rendered[path]]
    if check:
        require(
            not stale,
            "academy history projection is stale: "
            + ", ".join(path.name for path in stale),
        )
        print("ZHX academy history projection: current and idempotent (12/12)")
        return

    # All manifest, history, scope and idempotence checks above finish before
    # the first filesystem mutation. Each individual replacement is atomic.
    for path in stale:
        atomic_write(path, rendered[path])
    print(f"ZHX academy history projection: updated {len(stale)} file(s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if province history differs from the manifest projection",
    )
    args = parser.parse_args()
    run(args.check)


if __name__ == "__main__":
    main()
