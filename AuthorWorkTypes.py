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
from utils import author_works, count_work_types
from plots import plot_pie
from author_cli import make_author_parser

def author_work_types(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and the number of
    their works of each type, most common first.
    """
    author, items = author_works(c, author_id, from_date, to_date)
    return author, count_work_types(items)

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, counts = author_work_types(c, author_id, from_date, to_date)
    return [
        {"kind": "pie", "title": f"Types of works by {author['display_name']} from {from_date} to {to_date}",
         "data": counts},
        {"kind": "table", "header": ["Type", "Works"], "rows": list(counts.items())},
    ]

TOOL = {
    "name": "author_work_types",
    "label": "Work Types",
    "input": "author",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the pie chart. default is author_work_types.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="author_work_types.png")
    args = parser.parse_args()

    c = open_cache(args)

    author, counts = author_work_types(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    plot_pie(counts, args.output_file,
             f"Types of works by {author['display_name']} from {args.from_date} to {args.to_date}")
