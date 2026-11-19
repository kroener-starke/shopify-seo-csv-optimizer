"""Apply or verify approved introductions, a dedicated brand field and image captions."""

import argparse
import csv
import hashlib
import html
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate plan key {key!r}")
        result[key] = value
    return result


def read_table(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        columns = next(reader, [])
        if not columns or len(set(columns)) != len(columns):
            raise ValueError("missing or duplicate column headers")
        rows = list(reader)
    if any(len(row) != len(columns) for row in rows):
        raise ValueError("row width differs from header")
    return columns, rows


def column(columns, *names):
    hits = [i for i, name in enumerate(columns) if name in names]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one column from {names}")
    return hits[0]


def checked_text(value, label):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label}: expected nonempty plain text")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{label}: unexpected control character")
    return value


def apply_introduction(current, edits, name, version):
    intro = checked_text(edits.get("introduction"), name)
    escaped = html.escape(intro, quote=False)
    old_format = f"<p>{escaped}</p>\n"
    marked_tag = '<p class="fs-product-intro">'
    target = old_format if version == 1 else f"{marked_tag}{escaped}</p>\n"
    expected = edits.get("body_sha256")

    if "previous_introduction" in edits:
        previous = checked_text(edits["previous_introduction"], name)
        if version < 2 or previous == intro:
            raise ValueError(f"{name}: expected a different, previously marked introduction")
        prior = f"{marked_tag}{html.escape(previous, quote=False)}</p>\n"
        if current.startswith(prior) and digest(current) == expected:
            return target + current[len(prior):], "replaced_copied_introductions"
        if current.startswith(target) and digest(prior + current[len(target):]) == expected:
            return current, None
        raise ValueError(f"{name}: the marked introduction or original description has changed")

    if current.startswith(target):
        remainder = current[len(target):]
        accepted = {digest(current), digest(remainder)}
        if version >= 2:
            accepted.add(digest(old_format + remainder))
        if expected in accepted:
            return current, None
    elif version >= 2 and current.startswith(old_format):
        remainder = current[len(old_format):]
        if expected in {digest(current), digest(remainder)}:
            return target + remainder, "marked_existing_introductions"
    elif version >= 2 and current.startswith(marked_tag):
        raise ValueError(f"{name}: explicitly identify the opening paragraph to replace")
    elif digest(current) == expected:
        return target + current, "introductions"
    raise ValueError(f"{name}: original description has changed")


def apply_plan(columns, rows, plan):
    handle = column(columns, "Handle", "URL handle")
    title = column(columns, "Title")
    groups = defaultdict(list)
    for row in rows:
        groups[row[handle]].append(row)
    if not isinstance(plan, dict) or set(plan) - {"products", "version"} or not isinstance(plan.get("products"), dict):
        raise ValueError("expected an object containing products keyed by handle")
    version = plan.get("version", 1)
    if type(version) is not int or version not in (1, 2, 3):
        raise ValueError("unsupported plan version")
    counts = defaultdict(int)
    for name, edits in plan["products"].items():
        if not isinstance(edits, dict) or not edits or set(edits) - {"introduction", "previous_introduction", "body_sha256", "brand", "expected_brand", "images"}:
            raise ValueError(f"{name}: invalid or unknown edits")
        parents = [row for row in groups.get(name, []) if row[title].strip()]
        if len(parents) != 1:
            raise ValueError(f"{name}: expected one product row, found {len(parents)}")
        parent = parents[0]
        if {"introduction", "previous_introduction", "body_sha256"} & edits.keys():
            idx = column(columns, "Body (HTML)", "Description")
            parent[idx], change = apply_introduction(parent[idx], edits, name, version)
            if change:
                counts[change] += 1
            if version == 3:
                key = "product.metafields.custom.produkteinleitung"
                field = column(columns, *(c for c in columns if c == key or c.endswith(f" ({key})")))
                desired = edits["introduction"]
                if parent[field] not in ("", desired, edits.get("previous_introduction")):
                    raise ValueError(f"{name}: the saved product introduction has changed")
                if parent[field] != desired:
                    parent[field] = desired
                    counts["saved_introduction_fields"] += 1
        if "brand" in edits or "expected_brand" in edits:
            keys = [key for key in columns if key == "product.metafields.custom.produktmarke" or key.endswith(" (product.metafields.custom.produktmarke)")]
            idx = column(columns, *keys)
            value = checked_text(edits.get("brand"), name)
            if not isinstance(edits.get("expected_brand"), str) or parent[idx] not in (edits["expected_brand"], value):
                raise ValueError(f"{name}: brand source has changed")
            if parent[idx] != value:
                parent[idx] = value
                counts["brands"] += 1
        if "images" in edits:
            src = column(columns, "Image Src", "Product image URL")
            alt = column(columns, "Image Alt Text", "Image alt text")
            images = edits["images"]
            if not isinstance(images, dict):
                raise ValueError(f"{name}: images must be keyed by the current media URL")
            for url, edit in images.items():
                if not url or not isinstance(edit, dict) or set(edit) != {"expected_alt", "alt"} or not isinstance(edit["expected_alt"], str):
                    raise ValueError(f"{name}: malformed image edit")
                matches = [row for row in groups[name] if row[src] == url]
                if len(matches) != 1:
                    raise ValueError(f"{name}: missing or ambiguous media URL {url}")
                row = matches[0]
                value = checked_text(edit["alt"], name)
                if row[alt] not in (edit["expected_alt"], value):
                    raise ValueError(f"{name}: image caption has changed for {url}")
                if row[alt] != value:
                    row[alt] = value
                    counts["image_captions"] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("plan", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--verify", type=Path)
    args = parser.parse_args()
    columns, rows = read_table(args.source)
    plan = json.loads(args.plan.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    counts = apply_plan(columns, rows, plan)
    if args.verify:
        if read_table(args.verify) != (columns, rows):
            raise ValueError("output differs from the authorized plan or contains unrelated edits")
    else:
        if args.output.resolve() == args.source.resolve():
            raise ValueError("output must be a separate file")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=args.output.parent, delete=False) as temp:
            tmp = Path(temp.name)
            try:
                writer = csv.writer(temp)
                writer.writerow(columns)
                writer.writerows(rows)
                temp.close()
                os.link(tmp, args.output)  # Fail safely if another process has created the destination.
            finally:
                tmp.unlink(missing_ok=True)
    print(json.dumps({"rows": len(rows), "products_in_plan": len(plan["products"]), "changed": counts}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, csv.Error) as exc:
        raise SystemExit(str(exc)) from exc
