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

from pyalex_cache import pyalex_cache
import sys
import datetime
import argparse
import matplotlib.pyplot as plt

def combine_small_entries(data, threshold):
    """
    Combine entries whose count is less than `threshold` fraction of the
    total into a single "Other" category.
    """
    total = sum(data.values())
    if total == 0:
        return data

    main_entries = {}
    other_total = 0

    for label, count in data.items():
        if count / total < threshold:
            other_total += count
        else:
            main_entries[label] = count

    if other_total > 0:
        main_entries["Other"] = main_entries.get("Other", 0) + other_total

    return main_entries


def plot_pie_chart(data, output_path, from_date, to_date, search_term):
    labels = list(data.keys())
    sizes = list(data.values())

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        startangle=140,
    )
    ax.axis("equal")
    ax.set_title(f"Research Field Usage Distribution for papers containing '{search_term}' in the tile or abstract from {from_date} to {to_date}")

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

if __name__ == "__main__":
    c=pyalex_cache()

    #Get command line arguments
    # 1 positional argument is the search term
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the generated map. default is pie.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) threshold - The threshold for combining small entries into "Other". default is 0.02 (2%)
    # 8) show_other - If set to 1, will show the "Other" category in the pie chart. If set to 0, will not show the "Other" category. Default is 1.

    #Parse keyword arguments using argparse
    parser = argparse.ArgumentParser()

    #Positional argument for search term
    parser.add_argument("search_term", help="Search term for OpenAlex works. Example: 'GEANT4'")

    parser.add_argument("--from", dest="from_date", default=(datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d"), help="From publication date in YYYY-MM-DD format. Default is 1 year ago.")
    parser.add_argument("--to", dest="to_date", default=datetime.datetime.now().strftime("%Y-%m-%d"), help="To publication date in YYYY-MM-DD format. Default is today.")
    parser.add_argument("--use_cache", dest="use_cache", type=int, default=1, help="Use cache. 1 to use cache, 0 to not use cache. Default is 1.")
    parser.add_argument("--output", dest="output_file", default="pie.png", help="Output filename for the generated map. Default is pie.png.")
    parser.add_argument("--apikey", dest="apikey", default=None, help="OpenAlex API key. Default is no key.")
    parser.add_argument("--cache_file", dest="cache_file", default="cache.json.gz", help="Filename of the cache. Default is cache.json.gz.")
    parser.add_argument("--threshold", dest="threshold", type=float, default=0.02, help="Threshold for combining small entries into 'Other'. Default is 0.02 (2%).")
    parser.add_argument("--show_other", dest="show_other", type=int, default=1, help="Show 'Other' category in the pie chart. 1 to show, 0 to not show. Default is 1.")
    args = parser.parse_args()

    if args.use_cache:
        c.loadCache(args.cache_file)

    if args.apikey:
        c.setAPIKey(args.apikey)


    items = c.searchWorks(args.search_term, {"from_publication_date":args.from_date,"to_publication_date":args.to_date})
    imap={}
    for item in items:
        if not item.get('primary_topic',None):continue
        id = item['primary_topic']['display_name']
        if not id in imap: imap[id]=0
        imap[id]=imap[id]+1
    if args.use_cache:
        c.saveCache(args.cache_file)

    if args.show_other == 0:
        # Remove the "Other" category if it exists
        imap.pop("Other", None)
    imap = combine_small_entries(imap, args.threshold)
    plot_pie_chart(imap, args.output_file, args.from_date, args.to_date, args.search_term)