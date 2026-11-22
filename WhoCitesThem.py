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

from openalex_cli import CHECKBOX, add_options, open_cache, write_table
from plots import plot_bar_chart
from author_cli import make_author_parser
from utils import top_entries, author_works, count_authors, works_citing

def who_cites_them(c, author_id, from_date, to_date, include_self):
    """
    Return the author with the given OpenAlex ID or ORCID, the number of works
    citing any of their works published between from_date and to_date
    (inclusive) by each author, and each author's name, both keyed by the
    author's OpenAlex ID. The author themselves is left out unless
    `include_self` is set, as are authors with no OpenAlex ID.
    """
    author, items = author_works(c, author_id, from_date, to_date)
    workIds = []
    for item in items:
        workIds.append(item['id'].rsplit("/", 1)[-1])
    citing = works_citing(c, workIds)
    #count_authors leaves out the author it is given, so giving it None counts everyone
    excluded = author['id']
    if include_self:
        excluded = None
    counts, names = count_authors(citing, excluded)
    return author, counts, names

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, counts, names = who_cites_them(c, author_id, from_date, to_date, options["include_self"])
    #Different authors can share a name; the chart shows the highest count for each name
    nameCounts = {}
    for id, count in counts.items():
        nameCounts[names[id]] = max(nameCounts.get(names[id], 0), count)
    rows = []
    for id, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        rows.append([names[id], count, id, id])
    return [
        {"kind": "bar", "title": f"Authors citing works by {author['display_name']} from {from_date} to {to_date}",
         "data": top_entries(nameCounts, options["top"])},
        {"kind": "table", "header": ["Author", "Citing works", "OpenAlex ID", "PaperVis"],
         "types": [None, None, "asLink", "asUser"], "rows": rows},
    ]

TOOL = {
    "name": "who_cites_them",
    "label": "Who cites them",
    "input": "author",
    "options": [
        {"name": "top", "label": "Number of authors in the chart",
         "help": "Number of authors in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
        {"name": "include_self", "label": "Include the author",
         "help": "Count the author's citations of their own works. 1 to include, 0 to leave out. Default is 0.",
         "default": 0, "type": int, "choices": CHECKBOX},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date of the author's works default 1 year ago
    # 2) to - to_publication_date of the author's works default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is who_cites_them.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) top - The number of authors in the bar chart. default is 20
    # 8) include_self - If set to 1, will count the author's citations of their own works. If set to 0, will leave them out. Default is 0.
    # 9) table - The output filename for the table. default is who_cites_them.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="who_cites_them.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="who_cites_them.csv", help="Output filename for the table. Default is who_cites_them.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    author, counts, names = who_cites_them(c, args.author, args.from_date, args.to_date, args.include_self)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    nameCounts = {}
    for id, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        rows.append([id, names[id], count])
        nameCounts[names[id]] = max(nameCounts.get(names[id], 0), count)
    write_table(args.table_file, ["id", "name", "count"], rows)
    plot_bar_chart(top_entries(nameCounts, args.top),
                   args.output_file,
                   f"Authors citing works by {author['display_name']} from {args.from_date} to {args.to_date}",
                   "Number of citing works")
