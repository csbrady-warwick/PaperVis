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
from plots import plot_bar_chart
from paper_cli import make_paper_parser
from utils import citing_works

def citing_institution_types(c, doi, from_date, to_date):
    """
    Return the work with the given DOI and the number of works citing it by
    the types of their authors' institutions, such as education, company or
    government. A citing work counts once for each type.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    counts = {}
    for item in items:
        #Count each institution type at most once per paper
        seen=set()
        for author in item['authorships']:
            for institution in author['institutions']:
                institutionType = (institution.get('type') or "unclassified").capitalize()
                if institutionType in seen:
                    continue
                seen.add(institutionType)
                counts[institutionType] = counts.get(institutionType, 0) + 1
        #A paper with no institutions at all is counted as unclassified
        if not seen:
            counts["Unclassified"] = counts.get("Unclassified", 0) + 1
    return work, dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, counts = citing_institution_types(c, doi, from_date, to_date)
    return [
        {"kind": "bar",
         "title": f"Institution types of works citing '{work['display_name']}' from {from_date} to {to_date}",
         "data": counts},
        {"kind": "table", "header": ["Institution type", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "citing_institution_types",
    "label": "Citing institution types",
    "input": "paper",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is citing_institution_types.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) table - The output filename for the table. default is citing_institution_types.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing_institution_types.png")
    parser.add_argument("--table", dest="table_file", default="citing_institution_types.csv", help="Output filename for the table. Default is citing_institution_types.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, counts = citing_institution_types(c, args.doi, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    write_table(args.table_file, ["type", "count"], list(counts.items()))
    plot_bar_chart(counts, args.output_file,
                   f"Institution types of works citing '{work['display_name']}' from {args.from_date} to {args.to_date}",
                   "Number of works")
