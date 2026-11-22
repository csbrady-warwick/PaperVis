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

from openalex_cli import add_options, open_cache, write_table
from utils import search_works, top_entries, funder_types, count_funder_types
from plots import plot_bar_chart, plot_pie
from search_cli import make_search_parser

def funder_counts(c, search_term, from_date, to_date):
    """
    Count matching works per funder, keyed by the funder's OpenAlex ID, and
    return them with each funder's type, keyed the same way, and the number
    of matching works per funder type.
    """
    items = search_works(c, search_term, from_date, to_date)
    funders = {}
    for item in items:
        #Count each funder at most once per paper
        seen=set()
        for funder in item.get('funders', []):
            id = funder['id']
            if id in seen:
                continue
            seen.add(id)
            if id not in funders:
                funders[id] = {"name": funder['display_name'], "count": 0}
            funders[id]["count"] = funders[id]["count"] + 1
    types = funder_types(c, list(funders))
    return funders, types, count_funder_types(items, types)

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    funders, types, typeCounts = funder_counts(c, search_term, from_date, to_date)
    #Different funders can share a name; the chart shows the highest count for each name
    counts = {}
    groups = {}
    for id, funder in funders.items():
        if funder["count"] > counts.get(funder["name"], 0):
            counts[funder["name"]] = funder["count"]
            groups[funder["name"]] = types[id]
    rows = []
    for id, funder in sorted(funders.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([funder["name"], types[id], funder["count"], id])
    return [
        {"kind": "bar", "title": f"Funders of papers containing '{search_term}' from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"]), "groups": groups},
        {"kind": "pie", "title": f"Types of funders of papers containing '{search_term}' from {from_date} to {to_date}",
         "data": typeCounts},
        {"kind": "table", "header": ["Funder", "Type", "Works", "OpenAlex ID"],
         "types": [None, None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "funders",
    "label": "Funders",
    "input": "search",
    "options": [
        {"name": "top", "label": "Number of funders in the chart",
         "help": "Number of funders in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
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
    # 4) output - The output filename for the bar chart. default is funders.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) top - The number of funders in the bar chart. default is 20
    # 8) table - The output filename for the table. default is funders.csv
    # 9) types - The output filename for the pie chart of funder types. default is funder_types.png

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="funders.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="funders.csv", help="Output filename for the table. Default is funders.csv.")
    parser.add_argument("--types", dest="types_file", default="funder_types.png", help="Output filename for the pie chart of funder types. Default is funder_types.png.")
    args = parser.parse_args()

    c = open_cache(args)

    funders, types, typeCounts = funder_counts(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    groups = {}
    for id, funder in sorted(funders.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([id, funder["name"], types[id], funder["count"]])
        if funder["count"] > counts.get(funder["name"], 0):
            counts[funder["name"]] = funder["count"]
            groups[funder["name"]] = types[id]
    write_table(args.table_file, ["id", "name", "type", "count"], rows)
    plot_bar_chart(top_entries(counts, args.top),
                   args.output_file,
                   f"Funders of papers containing '{args.search_term}' from {args.from_date} to {args.to_date}",
                   "Number of works", groups)
    plot_pie(typeCounts, args.types_file,
             f"Types of funders of papers containing '{args.search_term}' from {args.from_date} to {args.to_date}")
