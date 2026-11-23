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

from openalex_cli import open_cache
from utils import search_works, full_works, count_international, percentages
from plots import plot_lines
from search_cli import make_search_parser

def international_collaboration(c, search_term, from_date, to_date):
    """
    Return the publication years and, for each, the number of matching works
    with at least one known author country and the number of those with
    authors in more than one country.
    """
    return count_international(full_works(c, search_works(c, search_term, from_date, to_date)))

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    years, knownCounts, internationalCounts = international_collaboration(c, search_term, from_date, to_date)
    values = percentages(knownCounts, internationalCounts)
    rows = []
    for year, knownCount, internationalCount, value in zip(years, knownCounts, internationalCounts, values):
        rows.append([year, knownCount, internationalCount, round(value, 1)])
    return [
        {"kind": "line",
         "title": f"International collaboration in papers containing '{search_term}' from {from_date} to {to_date}",
         "x": years, "series": {"International collaboration": values},
         "xlabel": "Publication year", "ylabel": "% of works with a known country"},
        {"kind": "table", "header": ["Year", "Works with a known country", "International", "%"], "rows": rows},
    ]

TOOL = {
    "name": "international",
    "label": "International Collaboration",
    "input": "search",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the chart. default is international.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="international.png")
    args = parser.parse_args()

    c = open_cache(args)

    years, knownCounts, internationalCounts = international_collaboration(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    plot_lines(years, {"International collaboration": percentages(knownCounts, internationalCounts)},
               args.output_file,
               f"International collaboration in papers containing '{args.search_term}' from {args.from_date} to {args.to_date}",
               "% of works with a known country")
