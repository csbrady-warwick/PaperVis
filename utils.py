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

import networkx

def search_works(c, search_term, from_date, to_date):
    """
    Search works published between from_date and to_date (inclusive).
    """
    return c.searchWorks(search_term, {"from_publication_date":from_date,"to_publication_date":to_date})

def topic_names(work, level, all_topics):
    """
    Return the set of names at `level` for a work's primary topic, or for all
    of its topics if `all_topics` is set.
    """
    if all_topics:
        topics = work.get('topics', [])
    elif work.get('primary_topic', None):
        topics = [work['primary_topic']]
    else:
        topics = []
    names = set()
    for topic in topics:
        if level == "topic":
            names.add(topic['display_name'])
        else:
            names.add(topic[level]['display_name'])
    return names

def top_entries(counts, top):
    """
    Return the `top` largest entries of a dictionary of counts, largest first.
    """
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top])

def report_only(c, stages):
    """
    Make the cache report progress only in the given stages, so that the
    searches a tool runs for each author do not make the progress shown flip
    between stages, and are not counted for progress that is never shown.
    Return the previous setting, to be restored afterwards by assigning it to
    c.reportedStages.
    """
    previous = c.reportedStages
    c.reportedStages = set(stages)
    return previous

def resolve_work(c, identifier):
    """
    Return the OpenAlex record of the work with the given DOI or OpenAlex
    work ID, each with or without its URL prefix.
    """
    if identifier.startswith("W") or identifier.startswith("https://openalex.org/"):
        work = c.getWork(identifier.rsplit("/", 1)[-1])
    elif identifier.startswith("https://doi.org/"):
        work = c.getWork(identifier)
    else:
        work = c.getWork("https://doi.org/" + identifier)
    if work is None:
        raise LookupError(f"No paper found in OpenAlex for '{identifier}'")
    return work

def citing_works(c, doi, from_date, to_date):
    """
    Return the work with the given DOI or OpenAlex work ID and the works
    citing it that were published between from_date and to_date (inclusive).
    """
    work = resolve_work(c, doi)
    items = c.filterWorks({"cites": work['id'].rsplit("/", 1)[-1],
                           "from_publication_date": from_date,
                           "to_publication_date": to_date})
    return work, items

def works_citing(c, workIds):
    """
    Return the works citing any of the works with the given short OpenAlex
    IDs, each once, whatever their publication date. The citing works are
    fetched for 50 works at a time, with progress reported as works done in
    the "citing" stage.
    """
    previous = report_only(c, ["citing"])
    found = {}
    try:
        for start in range(0, len(workIds), 50):
            for item in c.filterWorks({"cites": "|".join(workIds[start:start + 50])}):
                found[item['id']] = item
            c.report("citing", min(start + 50, len(workIds)), len(workIds))
    finally:
        c.reportedStages = previous
    return list(found.values())

def resolve_author(c, identifier):
    """
    Return the OpenAlex record of the author with the given OpenAlex ID or
    ORCID, each with or without its URL prefix.
    """
    if identifier.startswith("A") or identifier.startswith("https://openalex.org/"):
        author = c.getAuthor(identifier.rsplit("/", 1)[-1])
    else:
        author = c.getAuthor("https://orcid.org/" + identifier.rsplit("/", 1)[-1])
    if author is None:
        raise LookupError(f"No author found in OpenAlex for '{identifier}'")
    return author

def author_works(c, identifier, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID and their works
    published between from_date and to_date (inclusive).
    """
    author = resolve_author(c, identifier)
    items = c.filterWorks({"authorships.author.id": author['id'].rsplit("/", 1)[-1],
                           "from_publication_date": from_date,
                           "to_publication_date": to_date})
    return author, items

def count_authors(items, excludeId):
    """
    Return the number of works in `items` by each author other than the
    author with the full OpenAlex ID `excludeId` (None to count everyone),
    and each author's name, both keyed by the author's OpenAlex ID. Authors
    with no ID are left out.
    """
    counts = {}
    names = {}
    for item in items:
        #Count each author at most once per paper
        seen=set()
        for authorship in item['authorships']:
            otherId = authorship['author'].get('id')
            if not otherId or otherId == excludeId or otherId in seen:
                continue
            seen.add(otherId)
            counts[otherId] = counts.get(otherId, 0) + 1
            names[otherId] = authorship['author']['display_name']
    return counts, names

def count_co_authors(items, authorId):
    """
    Return the number of works in `items` that the author with the given full
    OpenAlex ID shares with each co-author, and each co-author's name, both
    keyed by the co-author's OpenAlex ID. Co-authors with no ID are left out.
    """
    return count_authors(items, authorId)

def co_author_counts(c, identifier, from_date, to_date):
    """
    Return the author with the given OpenAlex ID or ORCID, their works
    published between from_date and to_date (inclusive), the number of those
    works shared with each co-author, and each co-author's name, both keyed by
    the co-author's OpenAlex ID. Co-authors with no OpenAlex ID are left out.
    """
    author, items = author_works(c, identifier, from_date, to_date)
    shared, names = count_co_authors(items, author['id'])
    return author, items, shared, names

def co_author_counts_many(c, authorIds, from_date, to_date):
    """
    For each of many authors, given by full OpenAlex ID, return their works
    published between from_date and to_date (inclusive), the number shared
    with each co-author and each co-author's name, as co_author_counts does.
    The works of all the authors are fetched together, with progress reported
    as authors done in the "authors" stage.
    """
    shortIds = []
    for authorId in authorIds:
        shortIds.append(authorId.rsplit("/", 1)[-1])
    works = c.filterWorksForAuthors(shortIds, from_date, to_date, "authors")
    results = {}
    for authorId in authorIds:
        items = works[authorId.rsplit("/", 1)[-1]]
        shared, names = count_co_authors(items, authorId)
        results[authorId] = (items, shared, names)
    return results

def resolve_institution(c, identifier):
    """
    Return the OpenAlex record of the institution with the given OpenAlex ID
    or ROR ID, each with or without its URL prefix.
    """
    if identifier.startswith("I") or identifier.startswith("https://openalex.org/"):
        institution = c.getInstitution(identifier.rsplit("/", 1)[-1])
    else:
        institution = c.getInstitution("https://ror.org/" + identifier.rsplit("/", 1)[-1])
    if institution is None:
        raise LookupError(f"No institution found in OpenAlex for '{identifier}'")
    return institution

def institution_works(c, identifier, level, topicId, from_date, to_date):
    """
    Return the institution with the given OpenAlex ID or ROR ID and the works
    published between from_date and to_date (inclusive) that have it among
    their corresponding authors' institutions and have any topic within the
    field, subfield or topic with the given ID, as `level` says.
    """
    institution = resolve_institution(c, identifier)
    if level == "topic":
        topicFilter = "topics.id"
    else:
        topicFilter = f"topics.{level}.id"
    items = c.filterWorks({"corresponding_institution_ids": institution['id'].rsplit("/", 1)[-1],
                           topicFilter: topicId,
                           "from_publication_date": from_date,
                           "to_publication_date": to_date})
    return institution, items

def narrowest_topic(field, subfield, topic):
    """
    Return the level, "field", "subfield" or "topic", and the OpenAlex ID of
    the narrowest of a field, subfield and topic, any of which may be empty.
    """
    if topic:
        return "topic", topic
    if subfield:
        return "subfield", subfield
    return "field", field

def topic_name(c, level, topicId):
    """
    Return the name of the field, subfield or topic with the given short
    OpenAlex ID, as `level` says, or the level and ID if OpenAlex has no record
    of it.
    """
    record = c.getTopicLevel(level, topicId)
    if record is None:
        return f"{level} {topicId}"
    return record['display_name']

def layout_network(nodes, links):
    """
    Give each node of a network a position for drawing, with closely linked
    nodes drawn together. The layout is done once, so that the dashboard and
    the command line draw a network the same way.
    """
    graph = networkx.Graph()
    graph.add_nodes_from(nodes)
    for (first, second), count in links.items():
        graph.add_edge(first, second, weight=count)
    positions = networkx.spring_layout(graph, weight="weight", seed=1)
    for id in nodes:
        nodes[id]["x"] = float(positions[id][0])
        nodes[id]["y"] = float(positions[id][1])

def full_works(c, items):
    """
    Return search results with all of their authors.
    """
    #Search results list only the first authors of a large collaboration; a work's own record lists them all
    truncated = []
    for item in items:
        if item.get('is_authors_truncated'):
            truncated.append(item['id'].rsplit("/", 1)[-1])
    full = c.getWorks(truncated, "full_works")
    works = []
    for item in items:
        record = full.get(item['id'].rsplit("/", 1)[-1])
        if record is not None:
            works.append(record)
        else:
            works.append(item)
    return works

def count_funders(items):
    """
    Return the number of works in `items` per funder, with each funder's name,
    keyed by the funder's OpenAlex ID.
    """
    funders = {}
    for item in items:
        #Count each funder at most once per paper
        seen=set()
        for funder in item.get('funders', []):
            id = funder['id']
            if id in seen:
                continue
            seen.add(id)
            if id not in funders:
                funders[id] = {"name": funder['display_name'], "count": 0}
            funders[id]["count"] = funders[id]["count"] + 1
    return funders

def funder_types(c, funderIds):
    """
    Return the type of each funder with the given full OpenAlex ID, such as
    government or nonprofit, taken from the OpenAlex record of the same
    organisation as an institution, or "Unclassified" if there is none.
    """
    funders = c.getFunders(funderIds)
    institutionIds = {}
    for funderId in funderIds:
        institutionIds[funderId] = None
        if funders[funderId] is None:
            continue
        for role in funders[funderId].get('roles') or []:
            if role['role'] == "institution":
                institutionIds[funderId] = role['id']
    wanted = []
    for institutionId in institutionIds.values():
        if institutionId is not None and institutionId not in wanted:
            wanted.append(institutionId)
    institutions = c.getInstitutions(wanted)
    types = {}
    for funderId in funderIds:
        institutionId = institutionIds[funderId]
        if institutionId is not None and institutions[institutionId] and institutions[institutionId].get('type'):
            types[funderId] = institutions[institutionId]['type']
        else:
            types[funderId] = "Unclassified"
    return types

def count_funder_types(items, types):
    """
    Return the number of works in `items` per type of their funders, as given
    by `types`, keyed by funder ID, with each type counted at most once per work.
    """
    counts = {}
    for item in items:
        #Count each funder type at most once per paper
        seen=set()
        for funder in item.get('funders', []):
            funderType = types[funder['id']]
            if funderType in seen:
                continue
            seen.add(funderType)
            counts[funderType] = counts.get(funderType, 0) + 1
    return counts

def count_venues(items):
    """
    Return the number of works in `items` per primary venue, with each venue's
    name and type, keyed by the venue's OpenAlex ID. Works with no primary
    venue are skipped.
    """
    venues = {}
    for item in items:
        location = item.get('primary_location')
        if not location or not location.get('source'):
            continue
        source = location['source']
        id = source['id']
        if id not in venues:
            venues[id] = {"name": source['display_name'], "type": source.get('type'), "count": 0}
        venues[id]["count"] = venues[id]["count"] + 1
    return venues

def count_institutions(c, items, excludeId):
    """
    Return the number of works in `items` per institution of their authors,
    other than the institution with the full OpenAlex ID `excludeId`, each as
    [count, name, location], keyed by the institution's OpenAlex ID.
    """
    imap = {}
    for item in items:
        #Count each institution at most once per paper
        seen=set()
        for authorship in item['authorships']:
            for institution in authorship['institutions']:
                id = institution['id']
                if id == excludeId or id in seen:
                    continue
                seen.add(id)
                if id not in imap:
                    imap[id] = [0, institution['display_name'], None]
                imap[id][0] = imap[id][0] + 1
    #Look up each institution's location
    institutions = c.getInstitutions(list(imap))
    for id in imap:
        imap[id][2] = institutions[id]['geo'] if institutions[id] else None
    return imap

def count_institution_pairs(items, institutionIds):
    """
    Return the number of works in `items` on which both of a pair of the
    institutions with the given full OpenAlex IDs appear, keyed by the pair of
    IDs in sorted order.
    """
    wanted = set(institutionIds)
    pairs = {}
    for item in items:
        present = set()
        for authorship in item['authorships']:
            for institution in authorship['institutions']:
                if institution['id'] in wanted:
                    present.add(institution['id'])
        ordered = sorted(present)
        for first in range(len(ordered)):
            for second in range(first + 1, len(ordered)):
                key = (ordered[first], ordered[second])
                pairs[key] = pairs.get(key, 0) + 1
    return pairs

def works_with_few_authors(items, max_authors):
    """
    Return the works in `items` with at most `max_authors` authors. Search
    results cut short the author lists of large collaborations, so works whose
    lists are cut short are left out too, which is only correct for
    `max_authors` below 100.
    """
    works = []
    for item in items:
        if item.get('is_authors_truncated') or len(item['authorships']) > max_authors:
            continue
        works.append(item)
    return works

def count_external_authors(items, institutionId):
    """
    Return the number of works in `items` by each author whose authorship
    does not list the institution with the given full OpenAlex ID, each
    author's name, and the names of the institutions they list on those works,
    all keyed by the author's OpenAlex ID. Authors with no ID are left out.
    """
    counts = {}
    names = {}
    institutions = {}
    for item in items:
        #Count each author at most once per paper
        seen=set()
        for authorship in item['authorships']:
            authorId = authorship['author'].get('id')
            if not authorId or authorId in seen:
                continue
            institutionIds = []
            for institution in authorship['institutions']:
                institutionIds.append(institution['id'])
            if institutionId in institutionIds:
                continue
            seen.add(authorId)
            counts[authorId] = counts.get(authorId, 0) + 1
            names[authorId] = authorship['author']['display_name']
            institutions.setdefault(authorId, [])
            for institution in authorship['institutions']:
                if institution['display_name'] not in institutions[authorId]:
                    institutions[authorId].append(institution['display_name'])
    return counts, names, institutions

def count_local_authors(items, institutionId):
    """
    Return the number of works in `items` by each author whose authorship
    lists the institution with the given full OpenAlex ID, each author's name,
    and the names of the institutions they list on those works, all keyed by
    the author's OpenAlex ID. Authors with no ID are left out.
    """
    counts = {}
    names = {}
    institutions = {}
    for item in items:
        #Count each author at most once per paper
        seen=set()
        for authorship in item['authorships']:
            authorId = authorship['author'].get('id')
            if not authorId or authorId in seen:
                continue
            institutionIds = []
            for institution in authorship['institutions']:
                institutionIds.append(institution['id'])
            if institutionId not in institutionIds:
                continue
            seen.add(authorId)
            counts[authorId] = counts.get(authorId, 0) + 1
            names[authorId] = authorship['author']['display_name']
            institutions.setdefault(authorId, [])
            for institution in authorship['institutions']:
                if institution['display_name'] not in institutions[authorId]:
                    institutions[authorId].append(institution['display_name'])
    return counts, names, institutions

def count_countries(c, items, excludeId):
    """
    Return the number of works in `items` per country of their authors, other
    than authors at the institution with the full OpenAlex ID `excludeId`,
    keyed by country code, with each country's name taken from the OpenAlex
    record of an institution in that country. A country with no such
    institution is named by its code.
    """
    counts = {}
    candidates = {}
    for item in items:
        #Count each country at most once per paper
        seen=set()
        for authorship in item['authorships']:
            institutionIds = []
            for institution in authorship['institutions']:
                institutionIds.append(institution['id'])
            if excludeId in institutionIds:
                continue
            for code in authorship['countries']:
                if code in seen:
                    continue
                seen.add(code)
                counts[code] = counts.get(code, 0) + 1
            for institution in authorship['institutions']:
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
