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
from utils import search_works, top_entries
from plots import plot_bar_chart
from search_cli import make_search_parser
import plotly.graph_objects as go

def country_counts(c, search_term, from_date, to_date):
    """
    Count matching works per country code, with each country's name taken from
    the OpenAlex record of an institution in that country. A country with no
    such institution is named by its code.
    """
    items = search_works(c, search_term, from_date, to_date)
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
    return countries

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    countries = country_counts(c, search_term, from_date, to_date)
    locations = []
    values = []
    for country in countries.values():
        locations.append(country["name"])
        values.append(country["count"])
    rows = []
    for code, country in sorted(countries.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([code, country["name"], country["count"]])
    return [
        {"kind": "choropleth",
         "title": f"Countries publishing papers containing '{search_term}' from {from_date} to {to_date}",
         "locations": locations, "values": values},
        {"kind": "table", "header": ["Code", "Country", "Works"], "rows": rows},
    ]

TOOL = {
    "name": "countries",
    "label": "Countries",
    "input": "search",
    "options": [
        {"name": "top", "label": None,
         "help": "Number of countries in the bar chart. Default is 20.",
         "default": 20, "type": int, "choices": None},
    ],
    "views": views,
}

def plot_country_map(countries, output_path, search_term, from_date, to_date):
    names = []
    values = []
    for country in countries.values():
        names.append(country["name"])
        values.append(country["count"])
    figure = go.Figure(
        go.Choropleth(
            locations=names,
            locationmode="country names",
            z=values,
            text=names,
            colorscale="Blues",
            colorbar_title="Works",
        )
    )

    figure.update_geos(
        showcountries=True,
        countrycolor="white",
        coastlinecolor="gray",
        projection_type="natural earth",
    )

    figure.update_layout(
        title=f"Countries publishing papers using \"{search_term}\" in the abstract or title between {from_date} and {to_date} (inclusive)",
        height=700,
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
    )

    figure.write_html(output_path, include_plotlyjs=True)

    print(f"Map written to {output_path}")

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the bar chart. default is countries.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) top - The number of countries in the bar chart. default is 20
    # 8) table - The output filename for the table. default is countries.csv
    # 9) map - The output filename for the map. default is countries.html

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="countries.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="countries.csv", help="Output filename for the table. Default is countries.csv.")
    parser.add_argument("--map", dest="map_file", default="countries.html", help="Output filename for the map. Default is countries.html.")
    args = parser.parse_args()

    c = open_cache(args)

    countries = country_counts(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    rows = []
    counts = {}
    for code, country in sorted(countries.items(), key=lambda item: item[1]["count"], reverse=True):
        rows.append([code, country["name"], country["count"]])
        #Different codes can share a name; the chart shows the highest count for each name
        counts[country["name"]] = max(counts.get(country["name"], 0), country["count"])
    write_table(args.table_file, ["code", "name", "count"], rows)
    plot_bar_chart(top_entries(counts, args.top),
                   args.output_file,
                   f"Countries publishing papers containing '{args.search_term}' from {args.from_date} to {args.to_date}",
                   "Number of works")
    plot_country_map(countries, args.map_file, args.search_term, args.from_date, args.to_date)
