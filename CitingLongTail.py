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
from paper_cli import make_paper_parser
from utils import topic_names, citing_works

def citing_long_tail(c, doi, from_date, to_date, level, all_topics, threshold, min_count, examples):
    """
    Return the work with the given DOI or OpenAlex work ID and the entries at
    `level` of the works citing it that have at least `min_count` citing works
    but less than `threshold` fraction of the citing works that have any
    entry, largest first. Each entry has its name, count, share and up to
    `examples` example citing works.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    counts = {}
    works = {}
    total = 0
    for item in items:
        names = topic_names(item, level, all_topics)
        if names:
            total = total + 1
        for name in names:
            counts[name] = counts.get(name, 0) + 1
            works.setdefault(name, []).append(item)

    entries = []
    for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        share = count / total
        if count < min_count or share >= threshold:
            continue
        workExamples = []
        for example in works[name][:examples]:
            workExamples.append({"title": example['display_name'], "link": example.get('doi') or example['id']})
        entries.append({
            "name": name,
            "count": count,
            "share": share,
            "examples": workExamples,
        })
    return work, entries

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, entries = citing_long_tail(c, doi, from_date, to_date, options["level"], options["all_topics"],
                                     options["threshold"], options["min_count"], options["examples"])
    rows = []
    for entry in entries:
        examples = []
        for example in entry["examples"]:
            examples.append(f"{example['title']} ({example['link']})")
        rows.append([entry["name"], entry["count"], f"{entry['share']:.4f}", "; ".join(examples)])
    return [
        {"kind": "text",
         "text": f"Less common research fields of works citing '{work['display_name']}' from {from_date} to {to_date}"},
        {"kind": "table", "header": ["Field", "Citing works", "Share", "Examples"], "rows": rows},
    ]

TOOL = {
    "name": "citing_longtail",
    "label": "Long tail of citing fields",
    "input": "paper",
    "options": [
        LEVEL_OPTION,
        ALL_TOPICS_OPTION,
        {"name": "threshold", "label": "Leave out fields with this fraction of citing works or more",
         "help": "Fields with this fraction of citing works or more are left out. Default is 0.02.",
         "default": 0.02, "type": float, "choices": None},
        {"name": "min_count", "label": "Leave out fields with fewer citing works than",
         "help": "Fields with fewer citing works than this are left out. Default is 1.",
         "default": 1, "type": int, "choices": None},
        {"name": "examples", "label": "Example citing works per field",
         "help": "Number of example citing works listed for each field. Default is 3.",
         "default": 3, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI or OpenAlex work ID of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the table. default is citing_longtail.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) level - The topic level to group by: topic, subfield, field or domain. default is topic
    # 8) all_topics - If set to 1, will use all of a work's topics. If set to 0, will use only the primary topic. Default is 0.
    # 9) threshold - Fields with this fraction of citing works or more are left out. default is 0.02 (2%)
    # 10) min_count - Fields with fewer citing works than this are left out. default is 1
    # 11) examples - The number of example citing works listed for each field. default is 3

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing_longtail.csv")
    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    work, entries = citing_long_tail(c, args.doi, args.from_date, args.to_date,
                                     args.level, args.all_topics, args.threshold, args.min_count, args.examples)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for entry in entries:
        examples = []
        for example in entry["examples"]:
            examples.append(f"{example['title']} ({example['link']})")
        rows.append([entry["name"], entry["count"], f"{entry['share']:.4f}", "; ".join(examples)])
    write_table(args.output_file, ["name", "count", "share", "examples"], rows)
    print(f"{len(entries)} less common fields among the works citing '{work['display_name']}'")
