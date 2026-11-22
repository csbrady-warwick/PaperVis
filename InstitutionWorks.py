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
from institution_cli import make_institution_parser, topic_choice
from utils import institution_works, topic_name

def institution_papers(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID and its works,
    as institution_works chooses them, most cited first, each with its first
    corresponding author at the institution, if OpenAlex marks one.
    """
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    rows = []
    for item in sorted(items, key=lambda item: item['cited_by_count'], reverse=True):
        location = item.get('primary_location')
        source = location.get('source') if location else None
        authorName = ""
        authorId = ""
        for authorship in item['authorships']:
            if not authorship.get('is_corresponding'):
                continue
            institutionIds = []
            for affiliation in authorship['institutions']:
                institutionIds.append(affiliation['id'])
            if institution['id'] in institutionIds:
                authorName = authorship['author']['display_name']
                authorId = authorship['author'].get('id') or ""
                break
        rows.append({
            "title": item['display_name'],
            "date": item['publication_date'],
            "venue": source['display_name'] if source else "",
            "link": item.get('doi') or item['id'],
            "cited_by_count": item['cited_by_count'],
            "page": location.get('landing_page_url') if location else None,
            "author": authorName,
            "author_id": authorId,
        })
    return institution, rows

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, papers = institution_papers(c, identifier, options["topic_level"], options["topic_id"],
                                             from_date, to_date)
    #A browser table becomes slow with many thousands of rows, so only the most cited are shown
    shown = papers[:options["top"]]
    rows = []
    for row in shown:
        #The title links to the paper's page at its primary venue, where there is one
        title = row["title"]
        if row["page"]:
            title = {"text": row["title"], "link": row["page"]}
        rows.append([title, row["date"], row["venue"], row["link"], row["link"], row["author"], row["author_id"],
                     row["cited_by_count"]])
    return [
        {"kind": "text",
         "text": f"The {len(shown)} most cited of {len(papers)} works with a corresponding author at "
                 f"{institution['display_name']} in {options['topic_name']} "
                 f"published from {from_date} to {to_date}"},
        {"kind": "table",
         "header": ["Title", "Date", "Venue", "Link", "", "Corresponding author", "", "Citations"],
         "types": [None, None, None, "asLink", "asPaper", None, "asUser", None], "rows": rows},
    ]

TOOL = {
    "name": "institution_works",
    "label": "Works",
    "input": "institution",
    "options": [
        {"name": "top", "label": "Number of papers shown, most cited first",
         "help": None, "default": 200, "type": int, "choices": None},
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
    # 5) output - The output filename for the table of all the works. default is institution_works.csv
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_works.csv")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, papers = institution_papers(c, args.institution, level, topicId, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for row in papers:
        rows.append([row["title"], row["date"], row["venue"], row["link"], row["cited_by_count"],
                     row["author"], row["author_id"], row["page"] or ""])
    write_table(args.output_file, ["title", "date", "venue", "link", "cited_by_count",
                                   "corresponding_author", "corresponding_author_id", "page"], rows)
    print(f"{len(papers)} works with a corresponding author at {institution['display_name']} in {topicName} "
          f"published from {args.from_date} to {args.to_date}")
