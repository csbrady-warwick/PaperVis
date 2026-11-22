#! /usr/bin/env python3
#   Copyright 2026 University of Warwick, Scientific Computing RTP, Research Software Engineering Group
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from openalex_cli import LEVEL_OPTION, add_options, open_cache, write_table
from utils import search_works, topic_names
from search_cli import make_search_parser
import itertools
import matplotlib.pyplot as plt

def topic_pairs(c, search_term, from_date, to_date, level):
    """
    Count, across all topics of each matching work, how many works have each
    entry at `level` and how many have each unordered pair of entries.
    """
    items = search_works(c, search_term, from_date, to_date)
    entries = {}
    pairs = {}
    for item in items:
        names = sorted(topic_names(item, level, 1))
        for name in names:
            entries[name] = entries.get(name, 0) + 1
        for pair in itertools.combinations(names, 2):
            pairs[pair] = pairs.get(pair, 0) + 1
    return entries, pairs

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    entries, pairs = topic_pairs(c, search_term, from_date, to_date, options["level"])
    names = sorted(entries, key=lambda name: entries[name], reverse=True)[:options["top"]]
    index = {}
    matrix = []
    for position, name in enumerate(names):
        index[name] = position
        matrix.append([0] * len(names))
    for (first, second), count in pairs.items():
        if first in index and second in index:
            matrix[index[first]][index[second]] = count
            matrix[index[second]][index[first]] = count
    rows = []
    for (first, second), count in sorted(pairs.items(), key=lambda item: item[1], reverse=True):
        if count >= options["min_count"]:
            rows.append([first, second, count])
    return [
        {"kind": "heatmap",
         "title": f"Co-occurring research fields of papers containing '{search_term}' from {from_date} to {to_date}",
         "labels": names, "matrix": matrix, "colorbar": "Works with both"},
        {"kind": "table", "header": ["First", "Second", "Works"], "rows": rows},
    ]

TOOL = {
    "name": "pairs",
    "label": "Topic pairs",
    "input": "search",
    "options": [
        LEVEL_OPTION,
        {"name": "min_count", "label": "Leave out pairs with fewer works than",
         "help": "Pairs with fewer works than this are left out of the table. Default is 2.",
         "default": 2, "type": int, "choices": None},
        {"name": "top", "label": "Number of fields in the heatmap",
         "help": "Number of entries in the heatmap. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

def plot_heatmap(entries, pairs, output_path, top, search_term, from_date, to_date):
    names = sorted(entries, key=lambda name: entries[name], reverse=True)[:top]
    index = {}
    matrix = []
    for position, name in enumerate(names):
        index[name] = position
        matrix.append([0] * len(names))
    for (first, second), count in pairs.items():
        if first in index and second in index:
            matrix[index[first]][index[second]] = count
            matrix[index[second]][index[first]] = count

    fig, ax = plt.subplots(figsize=(12, 10))
    image = ax.imshow(matrix, cmap="viridis")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=90, fontsize="small")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize="small")
    fig.colorbar(image, ax=ax, label="Works with both")
    ax.set_title(f"Co-occurring research fields of papers containing '{search_term}' from {from_date} to {to_date}")

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the table. default is pairs.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) level - The topic level to group by: topic, subfield, field or domain. default is topic
    # 8) min_count - Pairs with fewer works than this are left out of the table. default is 2
    # 9) top - The number of entries in the heatmap. default is 20
    # 10) heatmap - The output filename for the heatmap. default is pairs.png

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="pairs.csv")
    add_options(parser, TOOL["options"])
    parser.add_argument("--heatmap", dest="heatmap_file", default="pairs.png", help="Output filename for the heatmap. Default is pairs.png.")
    args = parser.parse_args()

    c = open_cache(args)

    entries, pairs = topic_pairs(c, args.search_term, args.from_date, args.to_date, args.level)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for (first, second), count in sorted(pairs.items(), key=lambda item: item[1], reverse=True):
        if count >= args.min_count:
            rows.append([first, second, count])
    write_table(args.output_file, ["first", "second", "count"], rows)
    print(f"{len(rows)} pairs with at least {args.min_count} works")
    plot_heatmap(entries, pairs, args.heatmap_file, args.top, args.search_term, args.from_date, args.to_date)
