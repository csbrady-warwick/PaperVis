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
from utils import top_entries, count_venues, institution_works, topic_name
from institution_cli import make_institution_parser, topic_choice
from plots import plot_bar_chart

def institution_venues(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID and the number
    of its works, as institution_works chooses them, per primary venue, keyed
    by the venue's OpenAlex ID.
    """
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    return institution, count_venues(items)

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, venues = institution_venues(c, identifier, options["topic_level"], options["topic_id"],
                                             from_date, to_date)
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
        {"kind": "bar",
         "title": f"Venues of works by {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"]), "groups": groups},
        {"kind": "table", "header": ["Venue", "Type", "Works", "OpenAlex ID"],
         "types": [None, None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "institution_venues",
    "label": "Journals",
    "input": "institution",
    "options": [
        {"name": "top", "label": "Number of venues in the chart",
         "help": "Number of venues in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ROR ID of the institution
    # keyword arguments are
    # 1) field, subfield or topic - The OpenAlex ID of the field, subfield or topic. Exactly one is required
    # 2) from - from_publication_date default 1 year ago
    # 3) to - to_publication_date default today
    # 4) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 5) output - The output filename for the bar chart. default is institution_venues.png
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db
    # 8) top - The number of venues in the bar chart. default is 20
    # 9) table - The output filename for the table. default is institution_venues.csv

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_venues.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="institution_venues.csv", help="Output filename for the table. Default is institution_venues.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, venues = institution_venues(c, args.institution, level, topicId, args.from_date, args.to_date)
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
                   f"Venues of works by {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}",
                   "Number of works", groups)
