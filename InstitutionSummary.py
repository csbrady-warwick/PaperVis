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
from utils import institution_works, h_index, topic_name
from institution_cli import make_institution_parser, topic_choice

def institution_summary(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID, measures of
    its works, as institution_works chooses them, and OpenAlex's measures of
    the whole institution, each as a list of measure and value.
    """
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    citations = []
    tens = 0
    for item in items:
        citations.append(item['cited_by_count'])
        if item['cited_by_count'] >= 10:
            tens = tens + 1
    mean = 0
    if items:
        mean = round(sum(citations) / len(items), 2)
    chosen = [
        ["Works", len(items)],
        ["Citations", sum(citations)],
        ["Mean citations per work", mean],
        ["h-index", h_index(citations)],
        ["i10-index", tens],
    ]
    stats = institution['summary_stats']
    whole = [
        ["Works", institution['works_count']],
        ["Citations", institution['cited_by_count']],
        ["h-index", stats['h_index']],
        ["i10-index", stats['i10_index']],
        ["Two-year mean citedness", round(stats['2yr_mean_citedness'], 2)],
    ]
    return institution, chosen, whole

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, chosen, whole = institution_summary(c, identifier, options["topic_level"], options["topic_id"],
                                                     from_date, to_date)
    return [
        {"kind": "text",
         "text": f"Works with a corresponding author at {institution['display_name']} in {options['topic_name']} "
                 f"published from {from_date} to {to_date}"},
        {"kind": "table", "header": ["Measure", "Value"], "rows": chosen},
        {"kind": "text", "text": f"The whole of {institution['display_name']}, in all fields, as recorded by OpenAlex"},
        {"kind": "table", "header": ["Measure", "Value"], "rows": whole},
    ]

TOOL = {
    "name": "institution_summary",
    "label": "Summary",
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
    # 5) output - The output filename for the table. default is institution_summary.csv
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_summary.csv")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, chosen, whole = institution_summary(c, args.institution, level, topicId, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    print(f"Works with a corresponding author at {institution['display_name']} in {topicName} "
          f"published from {args.from_date} to {args.to_date}")
    for measure, value in chosen:
        print(f"  {measure}: {value}")
        rows.append(["chosen works", measure, value])
    print(f"The whole of {institution['display_name']}, in all fields, as recorded by OpenAlex")
    for measure, value in whole:
        print(f"  {measure}: {value}")
        rows.append(["whole institution", measure, value])
    write_table(args.output_file, ["scope", "measure", "value"], rows)
