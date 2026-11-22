#! /usr/bin/env python3
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
from utils import search_works
from search_cli import make_search_parser
import sys
import plotly.graph_objects as go

def plot_map(data, output_path, search_term, from_date, to_date):
    longitudes = []
    latitudes = []
    labels = []
    hover_text = []
    urls = []

    for key, value in data.items():
        if not isinstance(value, list) or len(value) < 3:
            continue

        number, name, info = value[:3]

        if not isinstance(info, dict):
            continue

        try:
            latitude = float(info["latitude"])
            longitude = float(info["longitude"])
        except (KeyError, TypeError, ValueError):
            continue

        latitudes.append(latitude)
        longitudes.append(longitude)
        labels.append(str(number))
        urls.append(str(key))

        hover_text.append(
            f"<b>{name}</b><br>"
            f"Number: {number}<br>"
            f"Click to open OpenAlex URL"
        )

    figure = go.Figure(
        go.Scattergeo(
            lon=longitudes,
            lat=latitudes,
            text=labels,
            customdata=urls,
            hovertext=hover_text,
            hoverinfo="text",
            mode="markers+text",
            textposition="middle center",
            marker={
                "size": 24,
                "color": "white",
                "line": {"color": "black", "width": 1},
            },
        )
    )

    figure.update_geos(
        showland=True,
        landcolor="lightgray",
        showocean=True,
        oceancolor="lightblue",
        showcountries=True,
        countrycolor="white",
        coastlinecolor="gray",
        projection_type="natural earth",
    )

    figure.update_layout(
        title=f"Institutions publishing papers using \"{search_term}\" in the abstract or title between {from_date} and {to_date} (inclusive)",
        height=700,
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
    )

    click_script = """
    var plot = document.getElementById('{plot_id}');
    plot.on('plotly_click', function(data) {
        var url = data.points[0].customdata;

        if (url) {
            window.open(url, '_blank', 'noopener,noreferrer');
        }
    });
    """

    figure.write_html(
        output_path,
        include_plotlyjs=True,
        post_script=click_script,
    )

    print(f"Map written to {output_path}")

def institution_counts(c, search_term, from_date, to_date):
    """
    Count matching works per institution, with each institution's name and location.
    """
    items = search_works(c, search_term, from_date, to_date)
    imap={}
    for item in items:
        #Count each institution at most once per paper
        seen=set()
        for author in item['authorships']:
            for institution in author['institutions']:
                id=institution['id']
                if id in seen:
                    continue
                seen.add(id)
                if (id not in imap):
                    imap[id]=[0,institution['display_name'], None]
                imap[id][0]=imap[id][0]+1
    #Look up each institution's location
    institutions = c.getInstitutions(list(imap))
    for id in imap:
        imap[id][2]=institutions[id]['geo'] if institutions[id] else None
    return imap

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    imap = institution_counts(c, search_term, from_date, to_date)
    rows = []
    for id, value in sorted(imap.items(), key=lambda item: item[1][0], reverse=True):
        rows.append([value[1], value[0], id])
    return [
        {"kind": "institution_map",
         "title": f"Institutions publishing papers containing '{search_term}' from {from_date} to {to_date}",
         "data": imap},
        {"kind": "table", "header": ["Institution", "Works", "OpenAlex ID"],
         "types": [None, None, "asLink"], "rows": rows},
    ]

TOOL = {
    "name": "map",
    "label": "Institution map",
    "input": "search",
    "options": [],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the generated map. default is map.html
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="map.html")
    args = parser.parse_args()

    c = open_cache(args)

    imap = institution_counts(c, args.search_term, args.from_date, args.to_date)
    if args.use_cache:
        c.saveCache(args.cache_file)

    plot_map(imap, args.output_file, args.search_term, args.from_date, args.to_date)
