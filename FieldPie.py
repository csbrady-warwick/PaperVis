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

from openalex_cli import CHECKBOX, add_options, open_cache
from utils import search_works
from search_cli import make_search_parser
import sys
import matplotlib.pyplot as plt

def combine_small_entries(data, threshold):
    """
    Combine entries whose count is less than `threshold` fraction of the
    total into a single "Other" category.
    """
    total = sum(data.values())
    if total == 0:
        return data

    main_entries = {}
    other_total = 0

    for label, count in data.items():
        if count / total < threshold:
            other_total += count
        else:
            main_entries[label] = count

    if other_total > 0:
        main_entries["Other"] = main_entries.get("Other", 0) + other_total

    return main_entries


def plot_pie_chart(data, output_path, from_date, to_date, search_term):
    labels = list(data.keys())
    sizes = list(data.values())

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
    )
    ax.axis("equal")
    ax.set_title(f"Research Field Usage Distribution for papers containing '{search_term}' in the title or abstract from {from_date} to {to_date}")

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

def field_counts(c, search_term, from_date, to_date):
    """
    Count matching works by their primary topic.
    """
    items = search_works(c, search_term, from_date, to_date)
    imap={}
    for item in items:
        if not item.get('primary_topic',None):continue
        id = item['primary_topic']['display_name']
        if not id in imap: imap[id]=0
        imap[id]=imap[id]+1
    return imap

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    counts = combine_small_entries(field_counts(c, search_term, from_date, to_date), options["threshold"])
    if options["show_other"] == 0:
        counts.pop("Other", None)
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [
        {"kind": "pie", "title": f"Research fields of papers containing '{search_term}' from {from_date} to {to_date}",
         "data": counts},
        {"kind": "table", "header": ["Field", "Works"], "rows": ordered},
    ]

TOOL = {
    "name": "pie",
    "label": "Field pie chart",
    "input": "search",
    "options": [
        {"name": "threshold", "label": "Fraction below which fields are grouped as Other",
         "help": "Threshold for combining small entries into 'Other'. Default is 0.02 (2%).",
         "default": 0.02, "type": float, "choices": None},
        {"name": "show_other", "label": "Show Other",
         "help": "Show 'Other' category in the pie chart. 1 to show, 0 to not show. Default is 1.",
         "default": 1, "type": int, "choices": CHECKBOX},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the generated map. default is pie.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) threshold - The threshold for combining small entries into "Other". default is 0.02 (2%)
    # 8) show_other - If set to 1, will show the "Other" category in the pie chart. If set to 0, will not show the "Other" category. Default is 1.

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="pie.png")

    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    imap = field_counts(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    imap = combine_small_entries(imap, args.threshold)
    if args.show_other == 0:
        # Remove the "Other" category if it exists
        imap.pop("Other", None)
    plot_pie_chart(imap, args.output_file, args.from_date, args.to_date, args.search_term)