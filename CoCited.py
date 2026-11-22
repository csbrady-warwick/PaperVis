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
from plots import plot_bar_chart
from paper_cli import make_paper_parser
from utils import citing_works

def co_cited(c, doi, from_date, to_date, top):
    """
    Return the work with the given DOI or OpenAlex work ID and the `top`
    works most often cited alongside it by the works citing it that were
    published between from_date and to_date (inclusive), each with the number
    of citing works that cite both.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    counts = {}
    for item in items:
        #Count each work at most once per citing work
        seen = set()
        for id in item['referenced_works']:
            if id == work['id'] or id in seen:
                continue
            seen.add(id)
            counts[id] = counts.get(id, 0) + 1
    ordered = sorted(counts.items(), key=lambda entry: entry[1], reverse=True)[:top]
    ids = []
    for id, count in ordered:
        ids.append(id.rsplit("/", 1)[-1])
    #Only the works shown are looked up, as there can be many thousands of co-cited works
    found = c.getWorks(ids, "co_cited")
    papers = []
    for id, count in ordered:
        record = found[id.rsplit("/", 1)[-1]]
        if record is None:
            papers.append({"title": id, "count": count, "link": id})
        else:
            papers.append({"title": record['display_name'], "count": count, "link": record.get('doi') or record['id']})
    return work, papers

def chart_counts(papers):
    """
    Return the number of co-citations of each paper, keyed by title.
    """
    #Different papers can share a title; the chart shows the highest count for each title
    counts = {}
    for paper in papers:
        counts[paper["title"]] = max(counts.get(paper["title"], 0), paper["count"])
    return counts

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, papers = co_cited(c, doi, from_date, to_date, options["top"])
    rows = []
    for paper in papers:
        rows.append([paper["title"], paper["count"], paper["link"], paper["link"]])
    return [
        {"kind": "bar",
         "title": f"Papers cited alongside '{work['display_name']}' by works published from {from_date} to {to_date}",
         "data": chart_counts(papers)},
        {"kind": "table", "header": ["Title", "Co-citations", "Link", "PaperVis"],
         "types": [None, None, "asLink", "asPaper"], "rows": rows},
    ]

TOOL = {
    "name": "co_cited",
    "label": "Co-cited papers",
    "input": "paper",
    "options": [
        {"name": "top", "label": "Number of co-cited papers shown",
         "help": "Number of co-cited papers looked up and shown. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI or OpenAlex work ID of the paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is co_cited.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) top - The number of co-cited papers looked up and shown. default is 20
    # 8) table - The output filename for the table. default is co_cited.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="co_cited.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="co_cited.csv", help="Output filename for the table. Default is co_cited.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, papers = co_cited(c, args.doi, args.from_date, args.to_date, args.top)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for paper in papers:
        rows.append([paper["title"], paper["count"], paper["link"]])
    write_table(args.table_file, ["title", "co_citations", "link"], rows)
    plot_bar_chart(chart_counts(papers),
                   args.output_file,
                   f"Papers cited alongside '{work['display_name']}' by works published from {args.from_date} to {args.to_date}",
                   "Number of citing works")
