"""Build an app-source caption plan from an original and a validated Shopify export."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from catalog_content import column, read_table


def prepare(source, updated):
    fields, before = source
    other_fields, after = updated
    if fields != other_fields or len(before) != len(after):
        raise ValueError("The exports must have the same headers and rows")
    handle = column(fields, "Handle", "URL handle")
    title = column(fields, "Title")
    image = column(fields, "Image Src", "Product image URL")
    alt = column(fields, "Image Alt Text", "Image alt text")
    campaign_key = "product.metafields.teeinblue.campaign_version"
    campaign = column(fields, *(f for f in fields if f == campaign_key or f.endswith(f" ({campaign_key})")))
    campaigns = {r[handle] for r in before if r[title] and r[campaign]}
    destinations = defaultdict(lambda: defaultdict(set))
    files = defaultdict(dict)
    for old, new in zip(before, after, strict=True):
        if (old[handle], old[image], old[campaign]) != (new[handle], new[image], new[campaign]):
            raise ValueError("Product, campaign or media association changed")
        name, url = old[handle], old[image]
        if name not in campaigns or not url:
            continue
        destinations[name][old[alt]].add(new[alt])
        if old[alt] != new[alt]:
            if not new[alt].strip() or url in files[name]:
                raise ValueError(f"{name}: missing caption or repeated source URL")
            files[name][url] = {"previous": old[alt], "caption": new[alt]}
    products = {}
    for name, items in files.items():
        mapping = {}
        needs_identity = []
        for url, item in items.items():
            previous = item["previous"]
            if previous and destinations[name][previous] == {item["caption"]}:
                mapping[previous] = item["caption"]
            else:
                needs_identity.append(url)
        products[name] = {"by_previous_caption": mapping, "images": items, "needs_media_match": needs_identity}
    return {"version": 1, "products": products}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("validated", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(read_table(args.source), read_table(args.validated))
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    print(f"{len(result['products'])} personalized products with changed photo captions")
