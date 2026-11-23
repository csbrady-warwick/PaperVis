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
from utils import search_works, count_open_access, by_year
from plots import plot_pie, plot_lines
from search_cli import make_search_parser

def open_access_counts(c, search_term, from_date, to_date):
    """
    Return the number of matching works with each open-access status, most
    common first, and the number with each status in each publication year.
    """
    return count_open_access(search_works(c, search_term, from_date, to_date))

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    counts, yearly = open_access_counts(c, search_term, from_date, to_date)
    title = f"Open access status of papers containing '{search_term}' from {from_date} to {to_date}"
    if options["by_year"]:
        years, series = by_year(counts, yearly)
        chart = {"kind": "line", "title": title, "x": years, "series": series,
                 "xlabel": "Publication year", "ylabel": "Number of works"}
    else:
        chart = {"kind": "pie", "title": title, "data": counts}
    return [
        chart,
        {"kind": "table", "header": ["Status", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "open_access",
    "label": "Open Access",
    "input": "search",
    "options": [
        {"name": "by_year", "label": "Plot each status by year",
         "help": "1 to plot the number of works with each status in each publication year, 0 to plot a pie chart. Default is 0.",
         "default": 0, "type": int, "choices": CHECKBOX},
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
    # 4) output - The output filename for the chart. default is open_access.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) by_year - If set to 1, will plot each status by publication year. If set to 0, will plot a pie chart. Default is 0.

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="open_access.png")
    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    counts, yearly = open_access_counts(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    title = f"Open access status of papers containing '{args.search_term}' from {args.from_date} to {args.to_date}"
    if args.by_year:
        years, series = by_year(counts, yearly)
        plot_lines(years, series, args.output_file, title, "Number of works")
    else:
        plot_pie(counts, args.output_file, title)
