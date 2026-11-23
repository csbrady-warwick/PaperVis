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
from plots import plot_bar_chart
from paper_cli import make_paper_parser
from utils import top_entries, citing_works

def citing_venues(c, doi, from_date, to_date):
    """
    Return the work with the given DOI and the number of works citing it per
    primary venue, keyed by the venue's OpenAlex ID. Works with no primary
    venue are skipped.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    venues = {}
    for item in items:
        location = item.get('primary_location')
        if not location or not location.get('source'):
            continue
        source = location['source']
        id = source['id']
        if id not in venues:
            venues[id] = {"name": source['display_name'], "type": source.get('type'), "count": 0}
        venues[id]["count"] = venues[id]["count"] + 1
    return work, venues

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, venues = citing_venues(c, doi, from_date, to_date)
    counts = {}
    groups = {}
    #Different venues can share a name; the chart shows the highest count for each name
    for venue in venues.values():
        if venue["count"] > counts.get(venue["name"], 0):
            counts[venue["name"]] = venue["count"]
            groups[venue["name"]] = venue["type"] or "Unknown"
    rows = []
    for id, venue in sorted(venues.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([venue["name"], venue["type"], venue["count"], id])
    return [
        {"kind": "bar", "title": f"Venues of works citing '{work['display_name']}' from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"]), "groups": groups},
        {"kind": "table", "header": ["Venue", "Type", "Works", "OpenAlex ID"],
         "types": [None, None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "citing_venues",
    "label": "Citing venues",
    "input": "paper",
    "options": [
        {"name": "top", "label": "Number of venues in the chart",
         "help": "Number of venues in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is citing_venues.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) top - The number of venues in the bar chart. default is 20
    # 8) table - The output filename for the table. default is citing_venues.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing_venues.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="citing_venues.csv", help="Output filename for the table. Default is citing_venues.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, venues = citing_venues(c, args.doi, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    groups = {}
    for id, venue in sorted(venues.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([id, venue["name"], venue["type"], venue["count"]])
        if venue["count"] > counts.get(venue["name"], 0):
            counts[venue["name"]] = venue["count"]
            groups[venue["name"]] = venue["type"] or "Unknown"
    write_table(args.table_file, ["id", "name", "type", "count"], rows)
    plot_bar_chart(top_entries(counts, args.top),
                   args.output_file,
                   f"Venues of works citing '{work['display_name']}' from {args.from_date} to {args.to_date}",
                   "Number of works", groups)
