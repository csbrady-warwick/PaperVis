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

from openalex_cli import open_cache
from utils import institution_works, count_work_types, topic_name
from plots import plot_pie
from institution_cli import make_institution_parser, topic_choice

def institution_work_types(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID and the number
    of its works, as institution_works chooses them, of each type, most common
    first.
    """
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    return institution, count_work_types(items)

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, counts = institution_work_types(c, identifier, options["topic_level"], options["topic_id"],
                                                 from_date, to_date)
    return [
        {"kind": "pie",
         "title": f"Types of works by {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "data": counts},
        {"kind": "table", "header": ["Type", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "institution_work_types",
    "label": "Work Types",
    "input": "institution",
    "options": [],
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
    # 5) output - The output filename for the pie chart. default is institution_work_types.png
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_work_types.png")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, counts = institution_work_types(c, args.institution, level, topicId, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    plot_pie(counts, args.output_file,
             f"Types of works by {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}")
