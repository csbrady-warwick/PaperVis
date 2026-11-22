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
from utils import resolve_author

def affiliation_history(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and their
    affiliations in the years from the year of from_date to the year of
    to_date, as recorded in the author's OpenAlex record, most recent first.
    Each has the institution's name, country code and OpenAlex ID and its
    years in that range.
    """
    author = resolve_author(c, author_id)
    first = int(from_date[:4])
    last = int(to_date[:4])
    rows = []
    for affiliation in author.get('affiliations', []):
        years = []
        for year in sorted(affiliation['years']):
            if first <= year <= last:
                years.append(year)
        if not years:
            continue
        institution = affiliation['institution']
        rows.append({
            "name": institution['display_name'],
            "country": institution.get('country_code') or "",
            "id": institution['id'],
            "years": years,
        })
    rows.sort(key=lambda row: row["years"][-1], reverse=True)
    return author, rows

def year_list(years):
    texts = []
    for year in years:
        texts.append(str(year))
    return ", ".join(texts)

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, affiliations = affiliation_history(c, author_id, from_date, to_date)
    rows = []
    for row in affiliations:
        rows.append([row["name"], row["country"], row["years"][0], row["years"][-1], year_list(row["years"]), row["id"]])
    return [
        {"kind": "text",
         "text": f"Affiliations of {author['display_name']} from {from_date[:4]} to {to_date[:4]}, as recorded by OpenAlex"},
        {"kind": "table", "header": ["Institution", "Country", "First year", "Last year", "Years", "OpenAlex ID"],
         "types": [None, None, None, None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "affiliation_history",
    "label": "Affiliation history",
    "input": "author",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - the first year of affiliations is the year of this date, default 1 year ago
    # 2) to - the last year of affiliations is the year of this date, default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the table. default is affiliation_history.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="affiliation_history.csv")
    args = parser.parse_args()

    c = open_cache(args)

    author, affiliations = affiliation_history(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for row in affiliations:
        rows.append([row["id"], row["name"], row["country"], row["years"][0], row["years"][-1], year_list(row["years"])])
    write_table(args.output_file, ["id", "name", "country", "first_year", "last_year", "years"], rows)
