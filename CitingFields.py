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

from openalex_cli import LEVEL_OPTION, ALL_TOPICS_OPTION, add_options, open_cache, write_table
from plots import plot_bar_chart
from paper_cli import make_paper_parser
from utils import topic_names, top_entries, citing_works

def citing_fields(c, doi, from_date, to_date, level, all_topics):
    """
    Return the work with the given DOI and the number of works citing it for
    each entry at `level`.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    counts = {}
    for item in items:
        for name in topic_names(item, level, all_topics):
            counts[name] = counts.get(name, 0) + 1
    return work, counts

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, counts = citing_fields(c, doi, from_date, to_date, options["level"], options["all_topics"])
    return [
        {"kind": "bar",
         "title": f"Research fields of works citing '{work['display_name']}' from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"])},
        {"kind": "table", "header": ["Field", "Works"],
         "rows": sorted(counts.items(), key=lambda item: item[1], reverse=True)},
    ]

TOOL = {
    "name": "citing_fields",
    "label": "Citing fields",
    "input": "paper",
    "options": [
        LEVEL_OPTION,
        ALL_TOPICS_OPTION,
        {"name": "top", "label": "Number of fields in the chart",
         "help": "Number of fields in the bar chart. Default is 20.",
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
    # 4) output - The output filename for the bar chart. default is citing_fields.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) level - The topic level to group by: topic, subfield, field or domain. default is topic
    # 8) all_topics - If set to 1, will use all of a work's topics. If set to 0, will use only the primary topic. Default is 0.
    # 9) top - The number of fields in the bar chart. default is 20
    # 10) table - The output filename for the table. default is citing_fields.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing_fields.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="citing_fields.csv", help="Output filename for the table. Default is citing_fields.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, counts = citing_fields(c, args.doi, args.from_date, args.to_date, args.level, args.all_topics)
    if args.use_cache:
        c.saveCache(args.cache_file)

    write_table(args.table_file, ["field", "count"],
                sorted(counts.items(), key=lambda item: item[1], reverse=True))
    plot_bar_chart(top_entries(counts, args.top), args.output_file,
                   f"Research fields of works citing '{work['display_name']}' from {args.from_date} to {args.to_date}",
                   "Number of works")
