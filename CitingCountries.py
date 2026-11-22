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
from plots import plot_country_map
from paper_cli import make_paper_parser
from utils import citing_works

def citing_countries(c, doi, from_date, to_date):
    """
    Return the work with the given DOI or OpenAlex work ID and the number of
    works citing it per country of their authors' institutions, keyed by
    country code, with each country's name taken from the OpenAlex record of
    an institution in that country. A country with no such institution is
    named by its code.
    """
    work, items = citing_works(c, doi, from_date, to_date)
    counts = {}
    candidates = {}
    for item in items:
        #Count each country at most once per paper
        seen=set()
        for author in item['authorships']:
            for code in author['countries']:
                if code in seen:
                    continue
                seen.add(code)
                counts[code] = counts.get(code, 0) + 1
            for institution in author['institutions']:
                code = institution.get('country_code')
                if code is not None:
                    candidates.setdefault(code, {})[institution['id']] = True
    #Name each country from the first of its institutions that can be looked up
    allIds = set()
    for codeIds in candidates.values():
        for id in codeIds:
            allIds.add(id)
    institutions = c.getInstitutions(list(allIds))
    names = {}
    for code, ids in candidates.items():
        for id in ids:
            if institutions[id]:
                names[code] = institutions[id]['geo']['country']
                break
    countries = {}
    for code, count in counts.items():
        countries[code] = {"name": names.get(code, code), "count": count}
    return work, countries

def views(c, doi, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    work, countries = citing_countries(c, doi, from_date, to_date)
    locations = []
    values = []
    rows = []
    for code, country in sorted(countries.items(), key=lambda item: item[1]["count"], reverse=True):
        locations.append(country["name"])
        values.append(country["count"])
        rows.append([code, country["name"], country["count"]])
    return [
        {"kind": "choropleth",
         "title": f"Countries of works citing '{work['display_name']}' from {from_date} to {to_date}",
         "locations": locations, "values": values},
        {"kind": "table", "header": ["Code", "Country", "Works"], "rows": rows},
    ]

TOOL = {
    "name": "citing_countries",
    "label": "Citing countries",
    "input": "paper",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the DOI or OpenAlex work ID of the cited paper
    # keyword arguments are
    # 1) from - from_publication_date of the citing papers default 1 year ago
    # 2) to - to_publication_date of the citing papers default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the map. default is citing_countries.html
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) table - The output filename for the table. default is citing_countries.csv

    #Parse keyword arguments using argparse
    parser = make_paper_parser()
    parser.set_defaults(output_file="citing_countries.html")
    parser.add_argument("--table", dest="table_file", default="citing_countries.csv", help="Output filename for the table. Default is citing_countries.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    work, countries = citing_countries(c, args.doi, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    for code, country in sorted(countries.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([code, country["name"], country["count"]])
    write_table(args.table_file, ["code", "name", "count"], rows)
    plot_country_map(countries, args.output_file,
                     f"Countries of works citing '{work['display_name']}' from {args.from_date} to {args.to_date}")
