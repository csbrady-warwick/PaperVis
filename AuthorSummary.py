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
from author_cli import make_author_parser
from utils import author_works, h_index

def author_summary(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID, measures of their
    works published between from_date and to_date (inclusive), and OpenAlex's
    measures of their whole career, each as a list of measure and value.
    """
    author, items = author_works(c, author_id, from_date, to_date)
    citations = []
    tens = 0
    for item in items:
        citations.append(item['cited_by_count'])
        if item['cited_by_count'] >= 10:
            tens = tens + 1
    mean = 0
    if items:
        mean = round(sum(citations) / len(items), 2)
    inRange = [
        ["Works", len(items)],
        ["Citations", sum(citations)],
        ["Mean citations per work", mean],
        ["h-index", h_index(citations)],
        ["i10-index", tens],
    ]
    stats = author['summary_stats']
    career = [
        ["Works", author['works_count']],
        ["Citations", author['cited_by_count']],
        ["h-index", stats['h_index']],
        ["i10-index", stats['i10_index']],
        ["Two-year mean citedness", round(stats['2yr_mean_citedness'], 2)],
    ]
    return author, inRange, career

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, inRange, career = author_summary(c, author_id, from_date, to_date)
    return [
        {"kind": "text", "text": f"Works by {author['display_name']} published from {from_date} to {to_date}"},
        {"kind": "table", "header": ["Measure", "Value"], "rows": inRange},
        {"kind": "text", "text": f"Whole career of {author['display_name']}, as recorded by OpenAlex"},
        {"kind": "table", "header": ["Measure", "Value"], "rows": career},
    ]

TOOL = {
    "name": "author_summary",
    "label": "Summary",
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
    # 4) output - The output filename for the table. default is author_summary.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="author_summary.csv")
    args = parser.parse_args()

    c = open_cache(args)

    author, inRange, career = author_summary(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    print(f"Works by {author['display_name']} published from {args.from_date} to {args.to_date}")
    for measure, value in inRange:
        print(f"  {measure}: {value}")
        rows.append(["date range", measure, value])
    print(f"Whole career of {author['display_name']}, as recorded by OpenAlex")
    for measure, value in career:
        print(f"  {measure}: {value}")
        rows.append(["career", measure, value])
    write_table(args.output_file, ["scope", "measure", "value"], rows)
