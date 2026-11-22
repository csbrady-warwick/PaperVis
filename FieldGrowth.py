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

from openalex_cli import CHECKBOX, LEVEL_OPTION, ALL_TOPICS_OPTION, add_options, open_cache
from utils import search_works, topic_names
from search_cli import make_search_parser
import matplotlib.pyplot as plt

def field_growth(c, search_term, from_date, to_date, level, all_topics, top, share):
    """
    Return the publication years and, for the `top` entries at `level` with the
    most works, the number of works in each year. If `share` is set, each
    number is divided by the number of matching works in that year.
    """
    items = search_works(c, search_term, from_date, to_date)
    totals = {}
    yearly = {}
    years = {}
    for item in items:
        year = item['publication_year']
        years[year] = years.get(year, 0) + 1
        for name in topic_names(item, level, all_topics):
            totals[name] = totals.get(name, 0) + 1
            yearly.setdefault(name, {})
            yearly[name][year] = yearly[name].get(year, 0) + 1

    allYears = sorted(years)
    series = {}
    for name in sorted(totals, key=lambda name: totals[name], reverse=True)[:top]:
        values = []
        for year in allYears:
            if share:
                values.append(yearly[name].get(year, 0) / years[year])
            else:
                values.append(yearly[name].get(year, 0))
        series[name] = values
    return allYears, series

def views(c, search_term, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    years, series = field_growth(c, search_term, from_date, to_date, options["level"], options["all_topics"],
                                 options["top"], options["share"])
    if options["share"]:
        ylabel = "Fraction of that year's works"
    else:
        ylabel = "Number of works"
    return [
        {"kind": "line", "title": f"Research fields of papers containing '{search_term}' from {from_date} to {to_date}",
         "x": years, "series": series, "xlabel": "Publication year", "ylabel": ylabel},
    ]

TOOL = {
    "name": "growth",
    "label": "Field growth",
    "input": "search",
    "options": [
        LEVEL_OPTION,
        ALL_TOPICS_OPTION,
        {"name": "top", "label": "Number of fields plotted",
         "help": "Number of entries plotted. Default is 10.",
         "default": 10, "type": int, "choices": None},
        {"name": "share", "label": "Plot fraction of each year's works",
         "help": "1 to plot the fraction of each year's works, 0 to plot the number of works. Default is 0.",
         "default": 0, "type": int, "choices": CHECKBOX},
    ],
    "views": views,
}

def plot_growth(years, series, output_path, search_term, from_date, to_date, share):
    fig, ax = plt.subplots(figsize=(12, 7))
    for name, values in series.items():
        ax.plot(years, values, marker="o", label=name)
    ax.set_xlabel("Publication year")
    ax.set_ylabel("Fraction of that year's works" if share else "Number of works")
    ax.set_xticks(years)
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
    ax.set_title(f"Research fields of papers containing '{search_term}' in the title or abstract from {from_date} to {to_date}")

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the chart. default is growth.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) level - The topic level to group by: topic, subfield, field or domain. default is topic
    # 8) all_topics - If set to 1, will use all of a work's topics. If set to 0, will use only the primary topic. Default is 0.
    # 9) top - The number of entries plotted. default is 10
    # 10) share - If set to 1, will plot the fraction of each year's works. If set to 0, will plot the number of works. Default is 0.

    #Parse keyword arguments using argparse
    parser = make_search_parser()
    parser.set_defaults(output_file="growth.png")
    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    years, series = field_growth(c, args.search_term, args.from_date, args.to_date,
                                 args.level, args.all_topics, args.top, args.share)
    if args.use_cache:
        c.saveCache(args.cache_file)

    plot_growth(years, series, args.output_file, args.search_term, args.from_date, args.to_date, args.share)
