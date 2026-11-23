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
from paper_cli import make_paper_parser
from utils import citing_works

def citing_papers(c, doi, from_date, to_date):
    """
    Return the work with the given DOI or OpenAlex work ID and the works
    citing it that were published between from_date and to_date (inclusive),
    most cited first.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    rows = []
    for item in sorted(items, key=lambda item: item['cited_by_count'], reverse=True):
        location = item.get('primary_location')
        source = location.get('source') if location else None
        rows.append({
            "title": item['display_name'],
            "date": item['publication_date'],
            "venue": source['display_name'] if source else "",
            "link": item.get('doi') or item['id'],
            "cited_by_count": item['cited_by_count'],
            "page": location.get('landing_page_url') if location else None,
        })
    return work, rows

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, citing = citing_papers(c, doi, from_date, to_date)
    rows = []
    for row in citing:
        #The title links to the paper's page at its primary venue, where there is one
        title = row["title"]
        if row["page"]:
            title = {"text": row["title"], "link": row["page"]}
        rows.append([title, row["date"], row["venue"], row["link"], row["link"], row["cited_by_count"]])
    return [
        {"kind": "text",
         "text": f"{len(citing)} works citing '{work['display_name']}' published from {from_date} to {to_date}"},
        {"kind": "table", "header": ["Title", "Date", "Venue", "Link", "PaperVis", "Citations"],
         "types": [None, None, None, "asLink", "asPaper", None], "rows": rows},
    ]

TOOL = {
    "name": "citing",
    "label": "Citing papers",
    "input": "paper",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the table. default is citing.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing.csv")
    args = parser.parse_args()

    c = open_cache(args)

    work, rows = citing_papers(c, args.doi, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    tableRows = []
    for row in rows:
        tableRows.append([row["title"], row["date"], row["venue"], row["link"], row["cited_by_count"]])
    write_table(args.output_file, ["title", "date", "venue", "link", "cited_by_count"], tableRows)
    print(f"{len(rows)} works citing '{work['display_name']}' published from {args.from_date} to {args.to_date}")
