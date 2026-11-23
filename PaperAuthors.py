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
from paper_cli import make_paper_parser
from utils import resolve_work

def paper_authors(c, doi):
    """
    Return the work with the given DOI or OpenAlex work ID and its authors in
    order, each with their ORCID, or their OpenAlex ID if they have no ORCID,
    or nothing if OpenAlex has neither, and the names of their institutions.
    """
    work = resolve_work(c, doi)
    rows = []
    for position, authorship in enumerate(work['authorships'], 1):
        author = authorship['author']
        if author.get('orcid'):
            identifier = author['orcid'].rsplit("/", 1)[-1]
            address = author['orcid']
        elif author.get('id'):
            identifier = author['id'].rsplit("/", 1)[-1]
            address = author['id']
        else:
            #OpenAlex leaves authors it could not resolve without an ID
            identifier = ""
            address = None
        affiliations = []
        for institution in authorship['institutions']:
            affiliations.append(institution['display_name'])
        rows.append({
            "position": position,
            "name": author['display_name'],
            "id": identifier,
            "address": address,
            "affiliations": "; ".join(affiliations),
        })
    return work, rows

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, authors = paper_authors(c, doi)
    rows = []
    for author in authors:
        #The identifier links to its ORCID or OpenAlex page, which differs from row to row
        identifierCell = author["id"]
        if author["address"]:
            identifierCell = {"text": author["id"], "link": author["address"]}
        rows.append([author["position"], author["name"], identifierCell, author["id"], author["affiliations"]])
    return [
        {"kind": "text", "text": f"Authors of '{work['display_name']}'"},
        {"kind": "table", "header": ["Position", "Author", "ORCID or OpenAlex ID", "PaperVis", "Affiliations"],
         "types": [None, None, None, "asUser", None], "rows": rows},
    ]

TOOL = {
    "name": "paper_authors",
    "label": "Authors",
    "input": "paper",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI or OpenAlex work ID of the paper
    # keyword arguments are
    # 1) from - not used by this tool
    # 2) to - not used by this tool
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the table. default is paper_authors.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="paper_authors.csv")
    args = parser.parse_args()

    c = open_cache(args)

    work, authors = paper_authors(c, args.doi)
    if args.use_cache:
        c.saveCache(args.cache_file)

    print(f"Authors of '{work['display_name']}'")
    rows = []
    for author in authors:
        print(f"{author['position']}. {author['name']}  {author['id']}  {author['affiliations']}")
        rows.append([author["position"], author["name"], author["id"], author["affiliations"]])
    write_table(args.output_file, ["position", "name", "id", "affiliations"], rows)
