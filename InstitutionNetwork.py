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
from utils import institution_works, works_with_few_authors, count_institutions, count_institution_pairs, layout_network, topic_name
from institution_cli import make_institution_parser, topic_choice
from plots import plot_network

#How each group of institutions is named in the network's legend
GROUP_NAMES = {0: "Institution", 1: "Partners"}

def institution_network(c, identifier, level, topicId, from_date, to_date, max_authors, max_institutions, min_shared):
    """
    Return the institution with the given OpenAlex ID or ROR ID and the
    network of its partners on its works, as institution_works chooses them,
    with at most `max_authors` authors (at most 99). The partners are the
    `max_institutions` other institutions sharing the most works, if they
    share at least `min_shared`; partners are linked to each other when they
    appear together on at least `min_shared` works. Also return the number of
    works used and the number found.
    """
    if max_authors > 99:
        raise ValueError(f"The maximum number of authors must be at most 99, not {max_authors}")
    institution, items = institution_works(c, identifier, level, topicId, from_date, to_date)
    small = works_with_few_authors(items, max_authors)
    imap = count_institutions(c, small, institution['id'])

    partners = []
    for id, value in sorted(imap.items(), key=lambda item: item[1][0], reverse=True):
        if value[0] < min_shared or len(partners) == max_institutions:
            break
        partners.append(id)

    nodes = {institution['id']: {"name": institution['display_name'], "depth": 0, "works": len(small)}}
    links = {}
    for id in partners:
        nodes[id] = {"name": imap[id][1], "depth": 1, "works": imap[id][0]}
        links[tuple(sorted((institution['id'], id)))] = imap[id][0]
    for pair, count in count_institution_pairs(small, partners).items():
        if count >= min_shared:
            links[pair] = count
    layout_network(nodes, links)
    return institution, nodes, links, len(small), len(items)

def views(c, identifier, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    institution, nodes, links, used, found = institution_network(
        c, identifier, options["topic_level"], options["topic_id"], from_date, to_date,
        options["max_authors"], options["max_institutions"], options["min_shared"])
    #Institutions have nothing to open in the dashboard, so clicking one does nothing
    for node in nodes.values():
        node["link"] = None
        node["hover"] = f"Works: {node['works']}"
    institutionRows = []
    for id, node in sorted(nodes.items(), key=lambda item: (item[1]["depth"], -item[1]["works"])):
        institutionRows.append([node["name"], node["works"], id])
    linkRows = []
    for (first, second), count in sorted(links.items(), key=lambda item: item[1], reverse=True):
        linkRows.append([nodes[first]["name"], nodes[second]["name"], count])
    summary = (f"{len(nodes) - 1} partner institutions of {institution['display_name']}, from {used} of {found} works; "
               f"works with more than {options['max_authors']} authors are left out")
    return [
        {"kind": "text", "text": summary},
        {"kind": "network",
         "title": f"Partner network of {institution['display_name']} in {options['topic_name']} "
                  f"from {from_date} to {to_date}",
         "nodes": nodes, "links": links, "groupNames": GROUP_NAMES},
        {"kind": "table", "header": ["Institution", "Shared works", "OpenAlex ID"],
         "types": [None, None, "asLink"], "rows": institutionRows},
        {"kind": "table", "header": ["Institution", "Institution", "Shared works"], "rows": linkRows},
    ]

TOOL = {
    "name": "institution_network",
    "label": "Partner network",
    "input": "institution",
    "options": [
        {"name": "max_authors", "label": "Leave out works with more than this many authors (at most 99)",
         "help": "Works with more than this many authors are left out. At most 99. Default is 10.",
         "default": 10, "type": int, "choices": None},
        {"name": "max_institutions", "label": "Maximum partner institutions",
         "help": "Most partner institutions shown, those sharing the most works first. Default is 50.",
         "default": 50, "type": int, "choices": None},
        {"name": "min_shared", "label": "Minimum shared works for a partner or link",
         "help": "Partners and links with fewer shared works than this are left out. Default is 2.",
         "default": 2, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ROR ID of the institution
    # keyword arguments are
    # 1) field, subfield or topic - The OpenAlex ID of the field, subfield or topic. Exactly one is required
    # 2) from - from_publication_date default 1 year ago
    # 3) to - to_publication_date default today
    # 4) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 5) output - The output filename for the network chart. default is institution_network.png
    # 6) apikey - The OpenAlex API key. default is no key
    # 7) cache_file - The filename of the cache. default is cache.db
    # 8) max_authors - Works with more than this many authors are left out, at most 99. default is 10
    # 9) max_institutions - The most partner institutions shown. default is 50
    # 10) min_shared - Partners and links with fewer shared works than this are left out. default is 2
    # 11) table - The output filename for the table of institutions. default is institution_network.csv
    # 12) links - The output filename for the table of links. default is institution_links.csv

    #Parse keyword arguments using argparse
    parser = make_institution_parser()
    parser.set_defaults(output_file="institution_network.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="institution_network.csv", help="Output filename for the table of institutions. Default is institution_network.csv.")
    parser.add_argument("--links", dest="links_file", default="institution_links.csv", help="Output filename for the table of links. Default is institution_links.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    level, topicId = topic_choice(args)
    topicName = topic_name(c, level, topicId)
    institution, nodes, links, used, found = institution_network(
        c, args.institution, level, topicId, args.from_date, args.to_date,
        args.max_authors, args.max_institutions, args.min_shared)
    if args.use_cache:
        c.saveCache(args.cache_file)

    institutionRows = []
    for id, node in sorted(nodes.items(), key=lambda item: (item[1]["depth"], -item[1]["works"])):
        institutionRows.append([id, node["name"], node["depth"], node["works"]])
    write_table(args.table_file, ["id", "name", "depth", "works"], institutionRows)
    linkRows = []
    for (first, second), count in sorted(links.items(), key=lambda item: item[1], reverse=True):
        linkRows.append([first, second, count])
    write_table(args.links_file, ["first", "second", "shared"], linkRows)
    plot_network(nodes, links, args.output_file,
                 f"Partner network of {institution['display_name']} in {topicName} from {args.from_date} to {args.to_date}",
                 GROUP_NAMES)
    print(f"{len(nodes) - 1} partner institutions found from {used} of {found} works")
