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

def self_citations(c, doi, from_date, to_date):
    """
    Return the work with the given DOI or OpenAlex work ID and the works
    citing it, each with the names of any authors it shares with the cited
    work. Authors with no OpenAlex ID cannot be matched, so they are left out.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    authors = set()
    for authorship in work['authorships']:
        if authorship['author'].get('id'):
            authors.add(authorship['author']['id'])
    rows = []
    for item in items:
        shared = []
        for authorship in item['authorships']:
            if authorship['author']['id'] in authors:
                shared.append(authorship['author']['display_name'])
        rows.append({
            "title": item['display_name'],
            "date": item['publication_date'],
            "link": item.get('doi') or item['id'],
            "shared": shared,
            "page": (item.get('primary_location') or {}).get('landing_page_url'),
        })
    return work, rows

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, citing = self_citations(c, doi, from_date, to_date)
    selfCount = 0
    rows = []
    for row in citing:
        if row["shared"]:
            selfCount = selfCount + 1
            #The title links to the paper's page at its primary venue, where there is one
            title = row["title"]
            if row["page"]:
                title = {"text": row["title"], "link": row["page"]}
            rows.append([title, row["date"], row["link"], row["link"], "; ".join(row["shared"])])
    return [
        {"kind": "text",
         "text": f"{selfCount} of {len(citing)} works citing '{work['display_name']}' share an author with it"},
        {"kind": "table", "header": ["Title", "Date", "Link", "PaperVis", "Shared authors"],
         "types": [None, None, "asLink", "asPaper", None], "rows": rows},
    ]

TOOL = {
    "name": "self_citations",
    "label": "Self-citations",
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
    # 4) output - The output filename for the table. default is self_citations.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="self_citations.csv")
    args = parser.parse_args()

    c = open_cache(args)

    work, rows = self_citations(c, args.doi, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    tableRows = []
    selfCount = 0
    for row in rows:
        if row["shared"]:
            tableRows.append([row["title"], row["date"], row["link"], "; ".join(row["shared"])])
            selfCount = selfCount + 1
    write_table(args.output_file, ["title", "date", "link", "shared_authors"], tableRows)
    print(f"{selfCount} of {len(rows)} works citing '{work['display_name']}' share an author with it")
