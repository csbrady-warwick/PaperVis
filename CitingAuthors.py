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
from paper_cli import make_paper_parser
from utils import top_entries, citing_works

def citing_authors(c, doi, from_date, to_date):
    """
    Return the work with the given DOI and the number of works citing it by
    each author, keyed by the author's OpenAlex ID.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    authors = {}
    for item in items:
        #Count each author at most once per paper
        seen=set()
        for authorship in item['authorships']:
            author = authorship['author']
            id = author['id']
            if id in seen:
                continue
            seen.add(id)
            if id not in authors:
                authors[id] = {"name": author['display_name'], "count": 0}
            authors[id]["count"] = authors[id]["count"] + 1
    return work, authors

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, authors = citing_authors(c, doi, from_date, to_date)
    #Different authors can share a name; the chart shows the highest count for each name
    counts = {}
    for author in authors.values():
        counts[author["name"]] = max(counts.get(author["name"], 0), author["count"])
    rows = []
    for id, author in sorted(authors.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([author["name"], author["count"], id, id])
    return [
        {"kind": "bar", "title": f"Authors of works citing '{work['display_name']}' from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"])},
        {"kind": "table", "header": ["Author", "Works", "OpenAlex ID", "PaperVis"],
         "types": [None, None, "asLink", "asUser"], "rows": rows},
    ]

TOOL = {
    "name": "citing_authors",
    "label": "Citing authors",
    "input": "paper",
    "options": [
        {"name": "top", "label": "Number of authors in the chart",
         "help": "Number of authors in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is citing_authors.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) top - The number of authors in the bar chart. default is 20
    # 8) table - The output filename for the table. default is citing_authors.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing_authors.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="citing_authors.csv", help="Output filename for the table. Default is citing_authors.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, authors = citing_authors(c, args.doi, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    for id, author in sorted(authors.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([id, author["name"], author["count"]])
        counts[author["name"]] = max(counts.get(author["name"], 0), author["count"])
    write_table(args.table_file, ["id", "name", "count"], rows)
    plot_bar_chart(top_entries(counts, args.top),
                   args.output_file,
                   f"Authors of works citing '{work['display_name']}' from {args.from_date} to {args.to_date}",
                   "Number of works")
