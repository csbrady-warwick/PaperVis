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
from utils import search_works
from search_cli import make_search_parser

def paper_list(c, search_term, from_date, to_date):
    """
    Return the works whose title or abstract matches the search term and that
    were published between from_date and to_date (inclusive), most cited first.
    """
    items = search_works(c, search_term, from_date, to_date)
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
    return rows

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    papers = paper_list(c, search_term, from_date, to_date)
    #A browser table becomes slow with many thousands of rows, so only the most cited are shown
    shown = papers[:options["top"]]
    rows = []
    for row in shown:
        #The title links to the paper's page at its primary venue, where there is one
        title = row["title"]
        if row["page"]:
            title = {"text": row["title"], "link": row["page"]}
        rows.append([title, row["date"], row["venue"], row["link"], row["link"], row["cited_by_count"]])
    return [
        {"kind": "text",
         "text": f"The {len(shown)} most cited of {len(papers)} works containing '{search_term}' "
                 f"published from {from_date} to {to_date}"},
        {"kind": "table", "header": ["Title", "Date", "Venue", "Link", "PaperVis", "Citations"],
         "types": [None, None, None, "asLink", "asPaper", None], "rows": rows},
    ]

TOOL = {
    "name": "papers",
    "label": "Papers",
    "input": "search",
    "options": [
        {"name": "top", "label": "Number of papers shown, most cited first",
         "help": None, "default": 200, "type": int, "choices": None},
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
    # 4) output - The output filename for the table of all matching works. default is papers.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="papers.csv")
    args = parser.parse_args()

    c = open_cache(args)

    papers = paper_list(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for row in papers:
        rows.append([row["title"], row["date"], row["venue"], row["link"], row["cited_by_count"], row["page"] or ""])
    write_table(args.output_file, ["title", "date", "venue", "link", "cited_by_count", "page"], rows)
    print(f"{len(papers)} works containing '{args.search_term}' published from {args.from_date} to {args.to_date}")
