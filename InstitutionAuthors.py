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
from utils import top_entries, institution_works, works_with_few_authors, count_local_authors, topic_name
from institution_cli import make_institution_parser, topic_choice
from plots import plot_bar_chart

def institution_authors(c, identifier, level, topicId, from_date, to_date, max_authors, min_works):
    """
    Return the institution with the given OpenAlex ID or ROR ID and the people
    at it on at least `min_works` of its works, as institution_works chooses
    them, with at most `max_authors` authors (at most 99), most works first.
    Each has their OpenAlex ID, name, number of works and the institutions
    they list on them. Also return the number of works used and the number
    found.
    """
    if max_authors > 99:
        raise ValueError(f"The maximum number of authors must be at most 99, not {max_authors}")
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    small = works_with_few_authors(items, max_authors)
    counts, names, institutions = count_local_authors(small, institution['id'])
    authors = []
    for id, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        if count < min_works:
            break
        authors.append({"id": id, "name": names[id], "count": count, "institutions": "; ".join(institutions[id])})
    return institution, authors, len(small), len(items)

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, authors, used, found = institution_authors(
        c, identifier, options["topic_level"], options["topic_id"], from_date, to_date,
        options["max_authors"], options["min_works"])
    #Different authors can share a name; the chart shows the highest count for each name
    counts = {}
    for author in authors:
        counts[author["name"]] = max(counts.get(author["name"], 0), author["count"])
    rows = []
    for author in authors:
        rows.append([author["name"], author["count"], author["institutions"], author["id"], author["id"]])
    summary = (f"{len(authors)} people at {institution['display_name']} on at least {options['min_works']} "
               f"of {used} works; {found - used} works with more than {options['max_authors']} authors are left out")
    return [
        {"kind": "text", "text": summary},
        {"kind": "bar",
         "title": f"Authors at {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "data": top_entries(counts, options["top"])},
        {"kind": "table", "header": ["Author", "Works", "Institutions", "OpenAlex ID", "PaperVis"],
         "types": [None, None, None, "asLink", "asUser"], "rows": rows},
    ]

TOOL = {
    "name": "institution_authors",
    "label": "Local authors",
    "input": "institution",
    "options": [
        {"name": "max_authors", "label": "Leave out works with more than this many authors (at most 99)",
         "help": "Works with more than this many authors are left out. At most 99. Default is 10.",
         "default": 10, "type": int, "choices": None},
        {"name": "min_works", "label": "Minimum works",
         "help": "People on fewer of the works than this are left out. Default is 2.",
         "default": 2, "type": int, "choices": None},
        {"name": "top", "label": "Number of people in the chart",
         "help": "Number of people in the bar chart. Default is 20.",
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
    # 5) output - The output filename for the bar chart. default is institution_authors.png
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db
    # 8) max_authors - Works with more than this many authors are left out, at most 99. default is 10
    # 9) min_works - People on fewer of the works than this are left out. default is 2
    # 10) top - The number of people in the bar chart. default is 20
    # 11) table - The output filename for the table. default is institution_authors.csv

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_authors.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="institution_authors.csv", help="Output filename for the table. Default is institution_authors.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, authors, used, found = institution_authors(
        c, args.institution, level, topicId, args.from_date, args.to_date, args.max_authors, args.min_works)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    for author in authors:
        rows.append([author["id"], author["name"], author["count"], author["institutions"]])
        counts[author["name"]] = max(counts.get(author["name"], 0), author["count"])
    write_table(args.table_file, ["id", "name", "count", "institutions"], rows)
    plot_bar_chart(top_entries(counts, args.top),
                   args.output_file,
                   f"Authors at {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}",
                   "Number of works")
