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
from author_cli import make_author_parser
from utils import resolve_author, co_author_counts_many, report_only, layout_network
from plots import plot_network

def co_author_network(c, author_id, from_date, to_date, depth, min_shared, max_authors):
    """
    Return the author with the given OpenAlex ID or ORCID, the authors found
    by going out from them through co-authorship for up to `depth` steps (1 to
    4), the links between them, and whether the search stopped early.
    `min_shared` is a comma-separated list of the number of papers a co-author
    must share to be followed and linked at each step out, the last value
    carrying on to any further steps, and at most `max_authors` authors have
    their works fetched. Each author
    has a name, a depth, a number of works (None if their works were not
    fetched) and a position for drawing; each link is keyed by the pair of
    author IDs and gives their number of shared papers.
    """
    if depth < 1 or depth > 4:
        raise ValueError(f"The depth must be from 1 to 4, not {depth}")
    #One minimum number of shared papers for each step out, the last carrying on to any further steps
    minimums = []
    try:
        for part in str(min_shared).split(","):
            minimums.append(int(part))
    except ValueError:
        raise ValueError(f"The minimum shared papers must be whole numbers separated by commas, not '{min_shared}'")
    root = resolve_author(c, author_id)
    nodes = {root['id']: {"name": root['display_name'], "depth": 0, "works": None}}
    links = {}
    frontier = [root['id']]
    expanded = 0
    truncated = False

    #Each author's own search reports progress, which would make the page flip between stages,
    #so only the expansion is reported while the network is built
    reportedStages = report_only(c, ["authors", "works"])
    try:
        for level in range(1, depth + 1):
            levelMinimum = minimums[min(level, len(minimums)) - 1]
            #The works of all the authors at this level are fetched together
            toExpand = frontier[:max_authors - expanded]
            if len(toExpand) < len(frontier):
                truncated = True
            expanded = expanded + len(toExpand)
            counted = co_author_counts_many(c, toExpand, from_date, to_date)
            nextFrontier = []
            for authorId in toExpand:
                items, shared, names = counted[authorId]
                nodes[authorId]["works"] = len(items)
                for otherId, count in shared.items():
                    if count < levelMinimum:
                        continue
                    key = tuple(sorted((authorId, otherId)))
                    links[key] = max(links.get(key, 0), count)
                    if otherId not in nodes:
                        nodes[otherId] = {"name": names[otherId], "depth": level, "works": None}
                        nextFrontier.append(otherId)
            frontier = nextFrontier
            if truncated:
                break
    finally:
        c.reportedStages = reportedStages

    layout_network(nodes, links)
    return root, nodes, links, truncated

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    root, nodes, links, truncated = co_author_network(c, author_id, from_date, to_date, options["depth"],
                                                      options["min_shared"], options["max_authors"])
    authorRows = []
    for id, node in sorted(nodes.items(), key=lambda item: (item[1]["depth"], item[1]["name"])):
        authorRows.append([node["name"], node["depth"], "" if node["works"] is None else node["works"], id, id])
    linkRows = []
    for (first, second), count in sorted(links.items(), key=lambda item: item[1], reverse=True):
        linkRows.append([nodes[first]["name"], nodes[second]["name"], count])
    summary = f"{len(nodes)} authors and {len(links)} links found from {root['display_name']}"
    if truncated:
        summary = summary + "; the search stopped early at the limit on authors to expand"
    return [
        {"kind": "text", "text": summary},
        {"kind": "network",
         "title": f"Co-authors of {root['display_name']} sharing at least {options['min_shared']} papers, from {from_date} to {to_date}",
         "nodes": nodes, "links": links},
        {"kind": "table", "header": ["Author", "Depth", "Works", "OpenAlex ID", "PaperVis"],
         "types": [None, None, None, "asLink", "asUser"], "rows": authorRows},
        {"kind": "table", "header": ["Author", "Author", "Shared papers"], "rows": linkRows},
    ]

TOOL = {
    "name": "co_author_network",
    "label": "Co-author network",
    "input": "author",
    "options": [
        {"name": "depth", "label": "Depth",
         "help": "Number of steps out from the author through co-authorship, from 1 to 4. Default is 2.",
         "default": 2, "type": int, "choices": ["1", "2", "3", "4"]},
        {"name": "min_shared", "label": "Minimum shared papers for a link, for each step out (such as 1,4,8)",
         "help": "Co-authors sharing fewer papers than this are not followed or linked. A comma-separated list such as 1,4,8 "
                 "gives a value for each step out from the author, the last carrying on to any further steps. Default is 4.",
         "default": "4", "type": str, "choices": None},
        {"name": "max_authors", "label": "Maximum authors to expand",
         "help": "Most authors whose works are fetched before the search stops. Default is 200.",
         "default": 200, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date default 1 year ago
    # 2) to - to_publication_date default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the network chart. default is co_author_network.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.db
    # 7) depth - The number of steps out from the author, from 1 to 4. default is 2
    # 8) min_shared - Co-authors sharing fewer papers than this are not followed or linked; a comma-separated list such as 1,4,8 gives a value for each step out. default is 4
    # 9) max_authors - The most authors whose works are fetched. default is 200
    # 10) table - The output filename for the table of authors. default is co_author_network.csv
    # 11) links - The output filename for the table of links. default is co_author_links.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="co_author_network.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="co_author_network.csv", help="Output filename for the table of authors. Default is co_author_network.csv.")
    parser.add_argument("--links", dest="links_file", default="co_author_links.csv", help="Output filename for the table of links. Default is co_author_links.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    root, nodes, links, truncated = co_author_network(c, args.author, args.from_date, args.to_date,
                                                      args.depth, args.min_shared, args.max_authors)
    if args.use_cache:
        c.saveCache(args.cache_file)

    authorRows = []
    for id, node in sorted(nodes.items(), key=lambda item: (item[1]["depth"], item[1]["name"])):
        authorRows.append([id, node["name"], node["depth"], "" if node["works"] is None else node["works"]])
    write_table(args.table_file, ["id", "name", "depth", "works"], authorRows)
    linkRows = []
    for (first, second), count in sorted(links.items(), key=lambda item: item[1], reverse=True):
        linkRows.append([first, second, count])
    write_table(args.links_file, ["first", "second", "shared"], linkRows)
    plot_network(nodes, links, args.output_file,
                 f"Co-authors of {root['display_name']} sharing at least {args.min_shared} papers, from {args.from_date} to {args.to_date}")
    print(f"{len(nodes)} authors and {len(links)} links found")
    if truncated:
        print("The search stopped early at the limit on authors to expand")
