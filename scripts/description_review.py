"""Find repeated storefront descriptions in an export, including previously introduced siblings."""

import re
import unicodedata
from collections import Counter, defaultdict
from html import unescape
from html.parser import HTMLParser


class VisibleText(HTMLParser):
    blocks = set("address article aside blockquote br dd div dl dt h1 h2 h3 h4 h5 h6 hr li ol p pre section table td th tr ul".split())

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script", "template"}:
            self.hidden += 1
        if tag in self.blocks:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"style", "script", "template"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in self.blocks:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def words(markup):
    parser = VisibleText()
    parser.feed(markup)
    parser.close()
    text = unicodedata.normalize("NFKC", "".join(parser.parts)).casefold()
    return tuple(re.findall(r"[^\W_]+", text))


def near_neighbors(texts):
    """Exact Jaccard join at 85% on four-word shingles; index the rare prefix."""
    features = {}
    frequency = Counter()
    for tokens in texts:
        if len(tokens) < 20:
            continue
        shingles = set(zip(tokens, tokens[1:], tokens[2:], tokens[3:]))
        features[tokens] = shingles
        frequency.update(shingles)
    postings = defaultdict(list)
    matches = defaultdict(dict)
    for tokens, shingles in features.items():
        count = len(shingles)
        prefix_size = count - (85 * count + 99) // 100 + 1
        prefix = sorted(shingles, key=lambda key: (frequency[key], key))[:prefix_size]
        possible = {other for key in prefix for other in postings[key]}
        for other in possible:
            other_set = features[other]
            if 100 * min(count, len(other_set)) < 85 * max(count, len(other_set)):
                continue
            common = len(shingles & other_set)
            union = count + len(other_set) - common
            if 100 * common >= 85 * union:
                matches[tokens][other] = matches[other][tokens] = round(common / union, 4)
        for key in prefix:
            postings[key].append(tokens)
    return matches


def review_descriptions(products):
    full = defaultdict(list)
    owners = defaultdict(list)
    openings = {}
    opening_frequency = Counter()
    empty = []
    saved_intro_review = {}
    for row in products:
        handle = row.get("Handle") or row.get("URL handle")
        if not handle:
            continue
        markup = row.get("Body (HTML)", row.get("Description", ""))
        field = "product.metafields.custom.produkteinleitung"
        saved = next((value for key, value in row.items()
                      if key == field or key.endswith(f" ({field})")), "")
        if saved:
            first = re.match(r'\s*<p class="fs-product-intro">(.*?)</p\s*>', markup, re.I | re.S)
            if not first:
                saved_intro_review[handle] = {"handle": handle, "reason": "restore saved product introduction"}
            elif unescape(first[1]).strip() != saved.strip():
                saved_intro_review[handle] = {"handle": handle, "reason": "marked opening and saved introduction differ"}
        tokens = words(markup)
        if not tokens:
            empty.append(handle)
            continue
        full[tokens].append(handle)
        # The editor prepends a simple standalone paragraph. Existing HTML following it
        # may have any format. Inspect only when there is a meaningful opening and tail.
        leading = re.match(r"\s*<p\b[^>]*>(.*?)</p\s*>", markup, re.I | re.S)
        if leading:
            opening = words(leading[1])
            tail = words(markup[leading.end():])
            if len(opening) >= 5 and tail:
                openings[handle] = opening, tail
                owners[tail].append(handle)
                opening_frequency[opening] += 1

    near = near_neighbors(dict.fromkeys([*full, *owners]))
    rows = []
    already_distinct = []
    for tokens, handles in full.items():
        for handle in handles:
            if handle in saved_intro_review:
                continue
            if len(handles) > 1:
                # All exact copies stay visible for editorial review, including a copied lead.
                rows.append({"handle": handle, "reason": "same visible description",
                             "example": handles[1] if handle == handles[0] else handles[0]})
                continue
            if handle in openings:
                opening, tail = openings[handle]
                related_bases = (tail, *near.get(tail, ()))
                evidence = any(sibling != handle for base in related_bases
                               for sibling in (*full.get(base, ()), *owners.get(base, ())))
                if opening_frequency[opening] == 1 and evidence:
                    already_distinct.append(handle)
                    continue
            # A new unedited sibling can match just the original body below another lead.
            example = next(iter(owners.get(tokens, ())), None)
            if example:
                rows.append({"handle": handle, "reason": "matches body below another introduction",
                             "example": example})
                continue
            for other, score in sorted(near.get(tokens, {}).items(), key=lambda pair: (-pair[1], pair[0])):
                candidates = full.get(other, []) + owners.get(other, [])
                example = next((candidate for candidate in candidates if candidate != handle), None)
                if example:
                    rows.append({"handle": handle, "reason": "similar description",
                                 "example": example, "four_word_jaccard": score})
                    break
    rows.extend(saved_intro_review.values())
    return {"review": sorted(rows, key=lambda row: row["handle"]),
            "exact_groups": [handles for handles in full.values() if len(handles) > 1],
            "distinct_openings_on_shared_copy": sorted(already_distinct),
            "empty": sorted(empty)}
