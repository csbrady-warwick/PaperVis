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
from utils import search_works, full_works, count_team_sizes, mean_by_year
from plots import plot_lines, plot_columns
from search_cli import make_search_parser

def team_sizes(c, search_term, from_date, to_date):
    """
    Return the number of matching works with each number of authors, in
    order of the number of authors, and the numbers of authors of the works
    in each publication year.
    """
    return count_team_sizes(full_works(c, search_works(c, search_term, from_date, to_date)))

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    counts, yearly = team_sizes(c, search_term, from_date, to_date)
    title = f"Number of authors of papers containing '{search_term}' from {from_date} to {to_date}"
    if options["by_year"]:
        years, means = mean_by_year(yearly)
        rows = []
        for year, mean in zip(years, means):
            rows.append([year, len(yearly[year]), round(mean, 2)])
        return [
            {"kind": "line", "title": title, "x": years, "series": {"Mean authors per work": means},
             "xlabel": "Publication year", "ylabel": "Mean number of authors"},
            {"kind": "table", "header": ["Year", "Works", "Mean authors"], "rows": rows},
        ]
    return [
        {"kind": "columns", "title": title, "data": counts, "ylabel": "Number of works"},
        {"kind": "table", "header": ["Authors", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "team_size",
    "label": "Team Size",
    "input": "search",
    "options": [
        {"name": "by_year", "label": "Plot mean by year",
         "help": "1 to plot the mean number of authors per work in each publication year, 0 to plot the number of works with each number of authors. Default is 0.",
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
    # 4) output - The output filename for the chart. default is team_size.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) by_year - If set to 1, will plot the mean number of authors per work in each publication year. If set to 0, will plot the number of works with each number of authors. Default is 0.

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="team_size.png")
    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    counts, yearly = team_sizes(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    title = f"Number of authors of papers containing '{args.search_term}' from {args.from_date} to {args.to_date}"
    if args.by_year:
        years, means = mean_by_year(yearly)
        plot_lines(years, {"Mean authors per work": means}, args.output_file, title, "Mean number of authors")
    else:
        plot_columns(counts, args.output_file, title, "Number of works")
