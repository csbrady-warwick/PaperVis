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
from utils import topic_names, co_author_counts, co_author_counts_many, report_only, layout_network
from plots import plot_network
import datetime

#How each group of authors is named in the network's legend
GROUP_NAMES = {0: "Author", 1: "Connecting co-authors", 2: "Possible reviewers"}

def matches_topic(item, topic):
    """
    Return whether any of a work's topics, or their subfields or fields, has a
    name containing `topic`, ignoring case.
    """
    text = topic.lower()
    for workTopic in item.get('topics', []):
        if text in workTopic['display_name'].lower():
            return True
        if text in workTopic['subfield']['display_name'].lower():
            return True
        if text in workTopic['field']['display_name'].lower():
            return True
    return False

def possible_reviewers(c, author_id, from_date, to_date, min_shared, conflict_years, min_career_years,
                       active_years, candidates, topic):
    """
    Return the author with the given OpenAlex ID or ORCID, their possible
    reviewers, and the network linking them. Possible reviewers have published
    with one of the author's close co-authors (those sharing at least
    `min_shared` of the author's works between from_date and to_date), but not
    with the author in the last `conflict_years` years or between from_date
    and to_date. They are ranked by how many close co-authors connect them to
    the author, then by their papers with those co-authors; the top
    `candidates` are checked, and those with no works in this year or the
    previous `active_years` years, or who first published less than
    `min_career_years` years ago, are left out. If `topic` is not blank, only
    papers whose topic, subfield or field name contains it link a candidate.
    """
    today = datetime.date.today()
    conflictFrom = (today - datetime.timedelta(days=round(365.25 * conflict_years))).isoformat()

    #Anyone who has published with the author recently, or in the dates searched, has a conflict of interest
    root, conflictItems, conflicted, conflictNames = co_author_counts(c, author_id, conflictFrom, today.isoformat())
    root, items, shared, names = co_author_counts(c, author_id, from_date, to_date)

    #The author's own research fields, to judge how close each candidate's work is
    rootFields = set()
    for item in items:
        rootFields.update(topic_names(item, "subfield", 0))

    connectors = []
    for otherId, count in shared.items():
        if count >= min_shared:
            connectors.append(otherId)

    found = {}
    connectorWorks = {}
    reportedStages = report_only(c, ["authors", "works", "checking"])
    try:
        #The works of all the connecting co-authors are fetched together
        counted = co_author_counts_many(c, connectors, from_date, to_date)
        for connectorId in connectors:
            connectorItems, connectorShared, connectorNames = counted[connectorId]
            connectorWorks[connectorId] = len(connectorItems)
            for item in connectorItems:
                if topic and not matches_topic(item, topic):
                    continue
                fields = topic_names(item, "subfield", 0)
                #Count each candidate at most once per paper
                seen=set()
                for authorship in item['authorships']:
                    candidateId = authorship['author'].get('id')
                    if (not candidateId or candidateId == root['id'] or candidateId == connectorId
                            or candidateId in conflicted or candidateId in shared or candidateId in seen):
                        continue
                    seen.add(candidateId)
                    if candidateId not in found:
                        found[candidateId] = {"name": authorship['author']['display_name'], "via": {}, "shared": 0,
                                              "fields": set()}
                    found[candidateId]["via"][connectorId] = found[candidateId]["via"].get(connectorId, 0) + 1
                    found[candidateId]["shared"] = found[candidateId]["shared"] + 1
                    found[candidateId]["fields"].update(fields)

        ranked = sorted(found.items(), key=lambda item: (len(item[1]["via"]), item[1]["shared"]), reverse=True)
        reviewers = []
        checked = ranked[:candidates]
        checkedIds = []
        for candidateId, candidate in checked:
            checkedIds.append(candidateId)
        #The author records give the works each candidate published in recent years
        records = c.getAuthors(checkedIds)
        for position, (candidateId, candidate) in enumerate(checked):
            c.report("checking", position, len(checked))
            lastYear = None
            if records[candidateId]:
                for entry in records[candidateId]['counts_by_year']:
                    if entry['works_count'] > 0 and (lastYear is None or entry['year'] > lastYear):
                        lastYear = entry['year']
            if lastYear is None or lastYear < today.year - active_years:
                continue
            candidate["last_year"] = lastYear
            firstYear = c.earliestPublicationYear(candidateId.rsplit("/", 1)[-1])
            if firstYear is None or today.year - firstYear < min_career_years:
                continue
            candidate["id"] = candidateId
            candidate["first_year"] = firstYear
            if candidate["fields"]:
                candidate["overlap"] = len(candidate["fields"] & rootFields) / len(candidate["fields"])
            else:
                candidate["overlap"] = 0.0
            reviewers.append(candidate)
    finally:
        c.reportedStages = reportedStages

    #The network shows the author, the co-authors connecting them to a reviewer, and the reviewers
    nodes = {root['id']: {"name": root['display_name'], "depth": 0, "works": len(items)}}
    links = {}
    for reviewer in reviewers:
        nodes[reviewer["id"]] = {"name": reviewer["name"], "depth": 2, "works": None}
        for connectorId, count in reviewer["via"].items():
            if connectorId not in nodes:
                nodes[connectorId] = {"name": names[connectorId], "depth": 1, "works": connectorWorks[connectorId]}
                links[tuple(sorted((root['id'], connectorId)))] = shared[connectorId]
            links[tuple(sorted((connectorId, reviewer["id"])))] = count
    layout_network(nodes, links)
    return root, reviewers, names, nodes, links, len(connectors)

def reviewer_rows(reviewers, names):
    """
    Return a table row for each possible reviewer: name, number of connecting
    co-authors, their names, shared papers, topic overlap, first and last
    publication years and OpenAlex ID.
    """
    rows = []
    for reviewer in reviewers:
        via = []
        for connectorId in reviewer["via"]:
            via.append(names[connectorId])
        rows.append([reviewer["name"], len(reviewer["via"]), "; ".join(via), reviewer["shared"],
                     f"{100 * reviewer['overlap']:.0f}%", reviewer["first_year"], reviewer["last_year"], reviewer["id"]])
    return rows

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    root, reviewers, names, nodes, links, connectorCount = possible_reviewers(
        c, author_id, from_date, to_date, options["min_shared"], options["conflict_years"],
        options["min_career_years"], options["active_years"], options["candidates"], options["topic"])
    rows = []
    for row in reviewer_rows(reviewers, names):
        rows.append(row + [row[-1]])
    summary = (f"{len(reviewers)} possible reviewers for {root['display_name']}, found through {connectorCount} close "
               f"co-authors; anyone who has published with them in the last {options['conflict_years']} years is left out")
    if options["topic"]:
        summary = summary + f"; only papers on '{options['topic']}' are counted"
    return [
        {"kind": "text", "text": summary},
        {"kind": "network",
         "title": f"Possible reviewers for {root['display_name']}, from {from_date} to {to_date}",
         "nodes": nodes, "links": links, "groupNames": GROUP_NAMES},
        {"kind": "table",
         "header": ["Possible reviewer", "Connecting co-authors", "Via", "Shared papers", "Topic overlap",
                    "First published", "Last published", "OpenAlex ID", "PaperVis"],
         "types": [None, None, None, None, None, None, None, "asLink", "asUser"], "rows": rows},
    ]

TOOL = {
    "name": "possible_reviewers",
    "label": "Possible reviewers",
    "input": "author",
    "options": [
        {"name": "min_shared", "label": "Minimum shared papers with a connecting co-author",
         "help": "Only co-authors sharing at least this many papers with the author are followed. Default is 4.",
         "default": 4, "type": int, "choices": None},
        {"name": "conflict_years", "label": "Leave out anyone who published with the author in the last N years",
         "help": "Anyone who has published with the author in this many years is left out. Default is 5.",
         "default": 5, "type": int, "choices": None},
        {"name": "min_career_years", "label": "Minimum years since first publication",
         "help": "Candidates who first published fewer than this many years ago are left out. Default is 5.",
         "default": 5, "type": int, "choices": None},
        {"name": "active_years", "label": "Must have published this year or in the previous N years",
         "help": "Candidates with no works in this year or this many previous years are left out. Default is 1.",
         "default": 1, "type": int, "choices": None},
        {"name": "candidates", "label": "Number of candidates to check",
         "help": "Number of top-ranked candidates whose first publication is checked. Default is 50.",
         "default": 50, "type": int, "choices": None},
        {"name": "topic", "label": "Only papers on this topic (blank for any)",
         "help": "Only papers whose topic, subfield or field name contains this text link a candidate. Default is any topic.",
         "default": "", "type": str, "choices": None, "suggest": "author_topics"},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date of the works searched default 1 year ago
    # 2) to - to_publication_date of the works searched default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the network chart. default is possible_reviewers.png
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) min_shared - Only co-authors sharing at least this many papers with the author are followed. default is 4
    # 8) conflict_years - Anyone who has published with the author in this many years is left out. default is 5
    # 9) min_career_years - Candidates who first published fewer than this many years ago are left out. default is 5
    # 10) active_years - Candidates with no works in this year or this many previous years are left out. default is 1
    # 11) candidates - The number of top-ranked candidates checked. default is 50
    # 12) topic - Only papers whose topic, subfield or field name contains this text link a candidate. default is any topic
    # 13) table - The output filename for the table. default is possible_reviewers.csv

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="possible_reviewers.png")
    add_options(parser, TOOL["options"])
    parser.add_argument("--table", dest="table_file", default="possible_reviewers.csv", help="Output filename for the table. Default is possible_reviewers.csv.")
    args = parser.parse_args()

    c = open_cache(args)

    root, reviewers, names, nodes, links, connectorCount = possible_reviewers(
        c, args.author, args.from_date, args.to_date, args.min_shared, args.conflict_years,
        args.min_career_years, args.active_years, args.candidates, args.topic)
    if args.use_cache:
        c.saveCache(args.cache_file)

    write_table(args.table_file, ["name", "connecting_co_authors", "via", "shared_papers", "topic_overlap",
                                  "first_published", "last_published", "id"], reviewer_rows(reviewers, names))
    plot_network(nodes, links, args.output_file,
                 f"Possible reviewers for {root['display_name']}, from {args.from_date} to {args.to_date}", GROUP_NAMES)
    print(f"{len(reviewers)} possible reviewers found through {connectorCount} close co-authors")
