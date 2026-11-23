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
from author_cli import make_author_parser
from utils import author_works
from plots import plot_map

def co_author_institutions(c, author_id, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and the number of
    their works per institution of their co-authors, with each institution's
    name and location. The author's own institutions are left out unless a
    co-author shares them.
    """
    author, items = author_works(c, author_id, from_date, to_date)
    imap = {}
    for item in items:
        #Count each institution at most once per paper
        seen=set()
        for authorship in item['authorships']:
            if authorship['author']['id'] == author['id']:
                continue
            for institution in authorship['institutions']:
                id = institution['id']
                if id in seen:
                    continue
                seen.add(id)
                if id not in imap:
                    imap[id] = [0, institution['display_name'], None]
                imap[id][0] = imap[id][0] + 1
    #Look up each institution's location
    institutions = c.getInstitutions(list(imap))
    for id in imap:
        imap[id][2] = institutions[id]['geo'] if institutions[id] else None
    return author, imap

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, imap = co_author_institutions(c, author_id, from_date, to_date)
    rows = []
    for id, value in sorted(imap.items(), key=lambda item: item[1][0], reverse=True):
        rows.append([value[1], value[0], id])
    return [
        {"kind": "institution_map",
         "title": f"Institutions of co-authors of {author['display_name']} from {from_date} to {to_date}",
         "data": imap},
        {"kind": "table", "header": ["Institution", "Shared works", "OpenAlex ID"],
         "types": [None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "co_author_map",
    "label": "Co-author institutions",
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
    # 4) output - The output filename for the map. default is co_author_map.html
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) table - The output filename for the table. default is co_author_institutions.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="co_author_map.html")
    parser.add_argument("--table", dest="table_file", default="co_author_institutions.csv", help="Output filename for the table. Default is co_author_institutions.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    author, imap = co_author_institutions(c, args.author, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for id, value in sorted(imap.items(), key=lambda item: item[1][0], reverse=True):
        rows.append([id, value[1], value[0]])
    write_table(args.table_file, ["id", "name", "count"], rows)
    plot_map(imap, args.output_file,
             f"Institutions of co-authors of {author['display_name']} from {args.from_date} to {args.to_date}")
