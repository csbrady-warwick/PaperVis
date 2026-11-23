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

from openalex_cli import MIN_WORKS_OPTION, add_options, open_cache, write_table
from utils import full_works, count_institutions, institution_works, topic_name, map_entries
from institution_cli import make_institution_parser, topic_choice
from plots import plot_map

def institution_partners(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID and the number
    of its works, as institution_works chooses them, per other institution of
    their authors, with each institution's name and location.
    """
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    return institution, count_institutions(c, full_works(c, items), institution['id'])

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, imap = institution_partners(c, identifier, options["topic_level"], options["topic_id"],
                                             from_date, to_date)
    rows = []
    for id, value in sorted(imap.items(), key=lambda item: item[1][0], reverse=True):
        rows.append([value[1], value[0], id])
    return [
        {"kind": "institution_map",
         "title": f"Partner institutions of {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "data": map_entries(imap, options["min_works"])},
        {"kind": "table", "header": ["Institution", "Shared works", "OpenAlex ID"],
         "types": [None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "institution_partners",
    "label": "Partner institutions",
    "input": "institution",
    "options": [MIN_WORKS_OPTION],
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
    # 5) output - The output filename for the map. default is institution_partners.html
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db
    # 8) table - The output filename for the table. default is institution_partners.csv
    # 9) min_works - Institutions with fewer works than this are not pinned on the map. default is 2

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_partners.html")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="institution_partners.csv", help="Output filename for the table. Default is institution_partners.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, imap = institution_partners(c, args.institution, level, topicId, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for id, value in sorted(imap.items(), key=lambda item: item[1][0], reverse=True):
        rows.append([id, value[1], value[0]])
    write_table(args.table_file, ["id", "name", "count"], rows)
    plot_map(map_entries(imap, args.min_works), args.output_file,
             f"Partner institutions of {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}")
