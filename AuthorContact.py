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
from utils import author_works

def author_contact(c, author_id, from_date, to_date, papers):
    """
    Return what OpenAlex holds that helps to contact the author with the given
    OpenAlex ID or ORCID: their record, their last known institutions with
    home pages, up to `papers` of their most recent works between from_date
    and to_date on which they are a corresponding author (whose publisher pages
    usually give an email address), and their full affiliations on those works,
    most recent first.
    """
    author, items = author_works(c, author_id, from_date, to_date)

    known = author.get('last_known_institutions') or []
    knownIds = []
    for institution in known:
        knownIds.append(institution['id'])
    records = c.getInstitutions(knownIds)
    institutions = []
    for institution in known:
        record = records[institution['id']]
        institutions.append({
            "id": institution['id'],
            "name": institution['display_name'],
            "country": institution.get('country_code') or "",
            "homepage": (record or {}).get('homepage_url') or "",
        })

    corresponding = []
    affiliations = {}
    for item in sorted(items, key=lambda item: item['publication_date'], reverse=True):
        for authorship in item['authorships']:
            if authorship['author'].get('id') != author['id']:
                continue
            #Keep each affiliation once, with the date of the most recent work giving it
            for affiliation in authorship.get('raw_affiliation_strings', []):
                if affiliation not in affiliations:
                    affiliations[affiliation] = item['publication_date']
            if authorship.get('is_corresponding') and len(corresponding) < papers:
                location = item.get('primary_location')
                source = location.get('source') if location else None
                corresponding.append({
                    "title": item['display_name'],
                    "date": item['publication_date'],
                    "venue": source['display_name'] if source else "",
                    "link": item.get('doi') or item['id'],
                    "page": location.get('landing_page_url') if location else None,
                })
    return author, institutions, corresponding, affiliations

def views(c, author_id, from_date, to_date, options):
    """
    Return descriptions of this tool's results for display.
    """
    author, institutions, corresponding, affiliations = author_contact(c, author_id, from_date, to_date, options["papers"])
    summary = f"Contact details held by OpenAlex for {author['display_name']}"
    if author.get('orcid'):
        summary = summary + f"; ORCID {author['orcid']}"
    institutionRows = []
    for institution in institutions:
        institutionRows.append([institution["name"], institution["country"], institution["homepage"], institution["id"]])
    paperRows = []
    for paper in corresponding:
        #The title links to the paper's page at its primary venue, where the email address is usually given
        title = paper["title"]
        if paper["page"]:
            title = {"text": paper["title"], "link": paper["page"]}
        paperRows.append([title, paper["date"], paper["venue"], paper["link"], paper["link"]])
    affiliationRows = []
    for affiliation, date in affiliations.items():
        affiliationRows.append([affiliation, date])
    return [
        {"kind": "text", "text": summary},
        {"kind": "table", "header": ["Last known institution", "Country", "Home page", "OpenAlex ID"],
         "types": [None, None, "asLink", "asLink"], "rows": institutionRows},
        {"kind": "table", "header": ["Recent paper as corresponding author", "Date", "Venue", "Link", "PaperVis"],
         "types": [None, None, None, "asLink", "asPaper"], "rows": paperRows},
        {"kind": "table", "header": ["Affiliation as given on papers", "Most recent"], "rows": affiliationRows},
    ]

TOOL = {
    "name": "author_contact",
    "label": "Contact details",
    "input": "author",
    "options": [
        {"name": "papers", "label": "Number of corresponding-author papers listed",
         "help": "Number of recent papers on which the author is a corresponding author to list. Default is 10.",
         "default": 10, "type": int, "choices": None},
    ],
    "views": views,
}

if __name__ == "__main__":
    #Get command line arguments
    # 1 positional argument is the OpenAlex ID or ORCID of the author
    # keyword arguments are
    # 1) from - from_publication_date of the works looked at default 1 year ago
    # 2) to - to_publication_date of the works looked at default today
    # 3) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 4) output - The output filename for the table of corresponding-author papers. default is author_contact.csv
    # 5) apikey - The OpenAlex API key. default is no key
    # 6) cache_file - The filename of the cache. default is cache.json.gz
    # 7) papers - The number of recent corresponding-author papers listed. default is 10

    #Parse keyword arguments using argparse
    parser = make_author_parser()
    parser.set_defaults(output_file="author_contact.csv")
    add_options(parser, TOOL["options"])
    args = parser.parse_args()

    c = open_cache(args)

    author, institutions, corresponding, affiliations = author_contact(c, args.author, args.from_date, args.to_date,
                                                                       args.papers)
    if args.use_cache:
        c.saveCache(args.cache_file)

    print(author['display_name'])
    if author.get('orcid'):
        print(f"ORCID: {author['orcid']}")
    for institution in institutions:
        print(f"Institution: {institution['name']} {institution['country']} {institution['homepage']}")
    for affiliation, date in affiliations.items():
        print(f"Affiliation ({date}): {affiliation}")
    rows = []
    for paper in corresponding:
        rows.append([paper["title"], paper["date"], paper["venue"], paper["link"], paper["page"] or ""])
    write_table(args.output_file, ["title", "date", "venue", "link", "page"], rows)
