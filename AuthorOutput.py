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

from openalex_cli import open_cache, write_table
from plots import plot_columns
from author_cli import make_author_parser
from utils import author_works

def author_output(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and the number of
    their works in each publication year, in order and including years with none.
    """
    author, items = author_works(c, author_id, from_date, to_date)
    counts = {}
    for item in items:
        year = item['publication_year']
        counts[year] = counts.get(year, 0) + 1
    filled = {}
    if counts:
        for year in range(min(counts), max(counts) + 1):
            filled[str(year)] = counts.get(year, 0)
    return author, filled

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, counts = author_output(c, author_id, from_date, to_date)
    return [
        {"kind": "columns", "title": f"Works by {author['display_name']} from {from_date} to {to_date}",
         "data": counts, "ylabel": "Number of works"},
        {"kind": "table", "header": ["Year", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "author_output",
    "label": "Publications per year",
    "input": "author",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the chart. default is author_output.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) table - The output filename for the table. default is author_output.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="author_output.png")
    parser.add_argument("--table", dest="table_file", default="author_output.csv", help="Output filename for the table. Default is author_output.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    author, counts = author_output(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    write_table(args.table_file, ["year", "count"], list(counts.items()))
    plot_columns(counts, args.output_file,
                 f"Works by {author['display_name']} from {args.from_date} to {args.to_date}", "Number of works")
