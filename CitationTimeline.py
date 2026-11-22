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
from paper_cli import make_paper_parser
from utils import citing_works
import matplotlib.pyplot as plt

def citation_timeline(c, doi, from_date, to_date, by):
    """
    Return the work with the given DOI and the number of works citing it in
    each publication year, or each month if `by` is "month", in order and
    including periods with none.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    counts = {}
    for item in items:
        if by == "month":
            period = item['publication_date'][:7]
        else:
            period = str(item['publication_year'])
        counts[period] = counts.get(period, 0) + 1

    if counts:
        first = min(counts)
        last = max(counts)
        if by == "month":
            periods = []
            year, month = int(first[:4]), int(first[5:7])
            while f"{year:04d}-{month:02d}" <= last:
                periods.append(f"{year:04d}-{month:02d}")
                month = month + 1
                if month > 12:
                    month = 1
                    year = year + 1
        else:
            periods = []
            for year in range(int(first), int(last) + 1):
                periods.append(str(year))
        filled = {}
        for period in periods:
            filled[period] = counts.get(period, 0)
        counts = filled
    return work, counts

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, counts = citation_timeline(c, doi, from_date, to_date, options["by"])
    return [
        {"kind": "columns", "title": f"Works citing '{work['display_name']}' from {from_date} to {to_date}",
         "data": counts, "ylabel": "Number of citing works"},
        {"kind": "table", "header": ["Period", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "timeline",
    "label": "Citations over time",
    "input": "paper",
    "options": [
        {"name": "by", "label": "Count per",
         "help": "Count citing works per year or per month. Default is year.",
         "default": "year", "type": str, "choices": ["year", "month"]},
    ],
    "views": views,
}

def plot_timeline(counts, output_path, title):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(list(counts.keys()), list(counts.values()))
    ax.set_ylabel("Number of citing works")
    ax.set_title(title)
    plt.xticks(rotation=90)

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the chart. default is citation_timeline.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) by - Count citing works per year or per month. default is year
    # 8) table - The output filename for the table. default is citation_timeline.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citation_timeline.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="citation_timeline.csv", help="Output filename for the table. Default is citation_timeline.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, counts = citation_timeline(c, args.doi, args.from_date, args.to_date, args.by)
    if args.use_cache:
        c.saveCache(args.cache_file)

    write_table(args.table_file, ["period", "count"], list(counts.items()))
    plot_timeline(counts, args.output_file,
                  f"Works citing '{work['display_name']}' from {args.from_date} to {args.to_date}")
