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
from utils import search_works, topic_names
from search_cli import make_search_parser
import statistics

def citation_stats(c, search_term, from_date, to_date, by, level, all_topics):
    """
    Return the number of works and the total, median and mean citation counts
    of matching works, grouped by publication year if `by` is "year" and by
    the entries at `level` otherwise.
    """
    items = search_works(c, search_term, from_date, to_date)
    groups = {}
    for item in items:
        if by == "year":
            keys = {item['publication_year']}
        else:
            keys = topic_names(item, level, all_topics)
        for key in keys:
            groups.setdefault(key, []).append(item['cited_by_count'])

    if by == "year":
        order = sorted(groups)
    else:
        order = sorted(groups, key=lambda key: len(groups[key]), reverse=True)
    stats = []
    for key in order:
        stats.append({
            "group": key,
            "count": len(groups[key]),
            "total": sum(groups[key]),
            "median": statistics.median(groups[key]),
            "mean": statistics.mean(groups[key]),
        })
    return stats

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    stats = citation_stats(c, search_term, from_date, to_date, options["by"], options["level"], options["all_topics"])
    rows = []
    for row in stats:
        rows.append([row["group"], row["count"], row["total"], row["median"], f"{row['mean']:.2f}"])
    return [
        {"kind": "table", "header": ["Group", "Works", "Total citations", "Median", "Mean"], "rows": rows},
    ]

TOOL = {
    "name": "citations",
    "label": "Citations",
    "input": "search",
    "options": [
        {"name": "by", "label": "Group by",
         "help": "Group by level or by year. Default is level.",
         "default": "level", "type": str, "choices": ["level", "year"]},
        LEVEL_OPTION,
        ALL_TOPICS_OPTION,
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
    # 4) output - The output filename for the table. default is citations.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) by - Group by level or by year. default is level
    # 8) level - The topic level to group by: topic, subfield, field or domain. default is topic
    # 9) all_topics - If set to 1, will use all of a work's topics. If set to 0, will use only the primary topic. Default is 0.

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="citations.csv")
    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    rows = citation_stats(c, args.search_term, args.from_date, args.to_date, args.by, args.level, args.all_topics)
    if args.use_cache:
        c.saveCache(args.cache_file)

    tableRows = []
    for row in rows:
        tableRows.append([row["group"], row["count"], row["total"], row["median"], f"{row['mean']:.2f}"])
    write_table(args.output_file, ["group", "count", "total", "median", "mean"], tableRows)
    print(f"{len(rows)} groups")
