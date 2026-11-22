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
from utils import top_entries, count_funders, institution_works, funder_types, count_funder_types, topic_name
from institution_cli import make_institution_parser, topic_choice
from plots import plot_bar_chart, plot_pie

def institution_funders(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID, the number of
    its works, as institution_works chooses them, per funder, keyed by the
    funder's OpenAlex ID, each funder's type, keyed the same way, and the
    number of its works per funder type.
    """
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    funders = count_funders(items)
    types = funder_types(c, list(funders))
    return institution, funders, types, count_funder_types(items, types)

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, funders, types, typeCounts = institution_funders(c, identifier, options["topic_level"],
                                                                  options["topic_id"], from_date, to_date)
    #Different funders can share a name; the chart shows the highest count for each name
    counts = {}
    groups = {}
    for id, funder in funders.items():
        if funder["count"] > counts.get(funder["name"], 0):
            counts[funder["name"]] = funder["count"]
            groups[funder["name"]] = types[id]
    rows = []
    for id, funder in sorted(funders.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([funder["name"], types[id], funder["count"], id])
    return [
        {"kind": "bar",
         "title": f"Funders of works by {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"]), "groups": groups},
        {"kind": "pie",
         "title": f"Types of funders of works by {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "data": typeCounts},
        {"kind": "table", "header": ["Funder", "Type", "Works", "OpenAlex ID"],
         "types": [None, None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "institution_funders",
    "label": "Funders",
    "input": "institution",
    "options": [
        {"name": "top", "label": "Number of funders in the chart",
         "help": "Number of funders in the bar chart. Default is 20.",
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
    # 5) output - The output filename for the bar chart. default is institution_funders.png
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db
    # 8) top - The number of funders in the bar chart. default is 20
    # 9) table - The output filename for the table. default is institution_funders.csv
    # 10) types - The output filename for the pie chart of funder types. default is institution_funder_types.png

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_funders.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="institution_funders.csv", help="Output filename for the table. Default is institution_funders.csv.")
    parser.add_argument("--types", dest="types_file", default="institution_funder_types.png", help="Output filename for the pie chart of funder types. Default is institution_funder_types.png.")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, funders, types, typeCounts = institution_funders(c, args.institution, level, topicId,
                                                                  args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    groups = {}
    for id, funder in sorted(funders.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([id, funder["name"], types[id], funder["count"]])
        if funder["count"] > counts.get(funder["name"], 0):
            counts[funder["name"]] = funder["count"]
            groups[funder["name"]] = types[id]
    write_table(args.table_file, ["id", "name", "type", "count"], rows)
    plot_bar_chart(top_entries(counts, args.top),
                   args.output_file,
                   f"Funders of works by {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}",
                   "Number of works", groups)
    plot_pie(typeCounts, args.types_file,
             f"Types of funders of works by {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}")
