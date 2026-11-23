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
from utils import resolve_author

def author_citations(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and the citations
    their work received in each year from the year of from_date to the year
    of to_date, as recorded in the author's OpenAlex record.
    """
    author = resolve_author(c, author_id)
    counts = {}
    for entry in sorted(author['counts_by_year'], key=lambda entry: entry['year']):
        if int(from_date[:4]) <= entry['year'] <= int(to_date[:4]):
            counts[str(entry['year'])] = entry['cited_by_count']
    return author, counts

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, counts = author_citations(c, author_id, from_date, to_date)
    return [
        {"kind": "columns", "title": f"Citations received by {author['display_name']} from {from_date} to {to_date}",
         "data": counts, "ylabel": "Citations"},
        {"kind": "table", "header": ["Year", "Citations"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "author_citations",
    "label": "Citations per year",
    "input": "author",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - start of the range of years default 1 year ago
    # 2) to - end of the range of years default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the chart. default is author_citations.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) table - The output filename for the table. default is author_citations.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="author_citations.png")
    parser.add_argument("--table", dest="table_file", default="author_citations.csv", help="Output filename for the table. Default is author_citations.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    author, counts = author_citations(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    write_table(args.table_file, ["year", "citations"], list(counts.items()))
    plot_columns(counts, args.output_file,
                 f"Citations received by {author['display_name']} from {args.from_date} to {args.to_date}", "Citations")
