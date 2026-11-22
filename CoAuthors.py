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
from plots import plot_bar_chart
from author_cli import make_author_parser
from utils import top_entries, author_works

def co_authors(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and the number of
    their works shared with each co-author, keyed by the co-author's OpenAlex ID.
    """
    author, items = author_works(c, author_id, from_date, to_date)
    coAuthors = {}
    for item in items:
        #Count each co-author at most once per paper
        seen=set()
        for authorship in item['authorships']:
            other = authorship['author']
            id = other['id']
            if id == author['id'] or id in seen:
                continue
            seen.add(id)
            if id not in coAuthors:
                coAuthors[id] = {"name": other['display_name'], "count": 0}
            coAuthors[id]["count"] = coAuthors[id]["count"] + 1
    return author, coAuthors

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, coAuthors = co_authors(c, author_id, from_date, to_date)
    counts = {}
    rows = []
    for id, coAuthor in sorted(coAuthors.items(), key=lambda item: item[1]["count"], reverse=True):
        #Different co-authors can share a name; the chart shows the highest count for each name
        counts[coAuthor["name"]] = max(counts.get(coAuthor["name"], 0), coAuthor["count"])
        rows.append([coAuthor["name"], coAuthor["count"], id, id])
    return [
        {"kind": "bar", "title": f"Co-authors of {author['display_name']} from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"])},
        {"kind": "table", "header": ["Co-author", "Shared works", "OpenAlex ID", "PaperVis"],
         "types": [None, None, "asLink", "asUser"], "rows": rows},
    ]

TOOL = {
    "name": "co_authors",
    "label": "Co-authors",
    "input": "author",
    "options": [
        {"name": "top", "label": "Number of co-authors in the chart",
         "help": "Number of co-authors in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is co_authors.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) top - The number of co-authors in the bar chart. default is 20
    # 8) table - The output filename for the table. default is co_authors.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="co_authors.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="co_authors.csv", help="Output filename for the table. Default is co_authors.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    author, coAuthors = co_authors(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    for id, coAuthor in sorted(coAuthors.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([id, coAuthor["name"], coAuthor["count"]])
        counts[coAuthor["name"]] = max(counts.get(coAuthor["name"], 0), coAuthor["count"])
    write_table(args.table_file, ["id", "name", "count"], rows)
    plot_bar_chart(top_entries(counts, args.top), args.output_file,
                   f"Co-authors of {author['display_name']} from {args.from_date} to {args.to_date}",
                   "Number of shared works")
