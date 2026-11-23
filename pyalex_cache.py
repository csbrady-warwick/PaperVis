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

import json

try:
    from pyalex import Works, Authors, Institutions, Keywords, config
    from pyalex.api import QueryError
    try:
        exact = Works.exact;
    except:
        def exact(self, text):
            """Find exactly matching works using exact search.
    
            Uses the search.exact parameter for exact match search

            Parameters
            ----------
            text : str
                Query text to find exact matching works

            Returns
            -------
            Works
                Updated object.
            """
            self._add_params("search.exact", text)
            return self
        Works.exact = exact
except ImportError:
    raise SystemExit("Please install pyalex: pip install pyalex")
from pyalex import Domains, Fields, Subfields, Topics, Funders

import json
import sys
import os
import datetime
import sqlite3
import zlib

#The table of records for each kind of OpenAlex object, by the pyalex class that fetches it
CLIENT_TABLES = {Works: "works", Authors: "authors", Institutions: "institutions", Funders: "funders",
                 Keywords: "keywords", Topics: "topics", Fields: "fields", Subfields: "subfields", Domains: "domains"}

#The same tables by the part of a full OpenAlex ID that names the kind of object: its first letter, or the path before the number
ID_TABLES = {"W": "works", "A": "authors", "I": "institutions", "F": "funders", "T": "topics",
             "keywords": "keywords", "fields": "fields", "subfields": "subfields", "domains": "domains"}

def tableFor(id):
    """Return the table of records for the object with the given full OpenAlex ID."""
    path = id.replace("https://openalex.org/", "")
    if "/" in path:
        return ID_TABLES[path.split("/")[0]]
    return ID_TABLES[path[0]]

def encode(value):
    """Return a value as compressed JSON, as it is stored in the database."""
    return zlib.compress(json.dumps(value).encode())

def decode(stored):
    """Return a value stored as compressed JSON."""
    return json.loads(zlib.decompress(stored))

class CacheDatabase:
    """
    The cache's SQLite database: a table of records for each kind of OpenAlex
    object, each record kept once and exactly as OpenAlex returned it; the
    searches made, the date ranges of each that are cached and the records
    each range returned, in order; and other lookups, such as autocomplete
    suggestions and identifiers that name nothing. Every change is committed
    as it is made.
    """

    def __init__(self):
        self.connection = None

    def open(self, filename):
        """Open the database, creating its tables if they do not exist."""
        #The dashboard's searches run in their own threads, one at a time
        self.connection = sqlite3.connect(filename, check_same_thread=False)
        #Write-ahead logging lets a second connection, such as the dashboard's lookups, work while a search writes
        self.connection.execute("PRAGMA journal_mode=WAL")
        with self.connection:
            self.connection.execute("DROP TABLE IF EXISTS cache")
            for table in set(ID_TABLES.values()):
                self.connection.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, fetched TEXT, "
                                        f"end_date TEXT, truncated INTEGER, record BLOB)")
            self.connection.execute("CREATE TABLE IF NOT EXISTS searches (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
            self.connection.execute("CREATE TABLE IF NOT EXISTS search_ranges (id INTEGER PRIMARY KEY, "
                                    "search_id INTEGER REFERENCES searches(id), start_date TEXT, end_date TEXT, "
                                    "created TEXT, stable_date TEXT)")
            self.connection.execute("CREATE INDEX IF NOT EXISTS search_ranges_search ON search_ranges (search_id)")
            self.connection.execute("CREATE TABLE IF NOT EXISTS search_results (range_id INTEGER REFERENCES search_ranges(id), "
                                    "position INTEGER, record_id TEXT, PRIMARY KEY (range_id, position))")
            self.connection.execute("CREATE TABLE IF NOT EXISTS lookups (key TEXT PRIMARY KEY, created TEXT, "
                                    "end_date TEXT, value BLOB)")

    def __contains__(self, key):
        """Return whether a lookup with the given key is stored."""
        return self.connection.execute("SELECT 1 FROM lookups WHERE key = ?", (key,)).fetchone() is not None

class pyalex_cache:

    def __init__(self):
        """Initialize cache storage and refresh intervals."""
        self.defaultPerPage=200
        self.fetchGaps = True
        self.progress = None
        #While refresh is set, each cache entry is treated as missing the first time it is asked for, so it is fetched afresh
        self.refresh = False
        self.refreshed = set()
        #While set, only progress in these stages is reported, and searches are only counted if "search" is among them
        self.reportedStages = None
        #Until a cache file is opened, the database is held in memory, so nothing is kept between runs
        self.cache = CacheDatabase()
        self.cache.open(":memory:")
        self.shortCache=datetime.timedelta(hours=1).total_seconds()
        self.longCache = datetime.timedelta(days=30).total_seconds()
        self.stableTime = datetime.timedelta(days=100).total_seconds()

    def loadCache(self, filename):
        """Open the cache database, creating it if it does not exist."""
        self.cache.open(filename)

    def saveCache(self, filename, force=False):
        """Commit any change not yet written to the database; changes are normally committed as they are made."""
        self.cache.connection.commit()

    def isFresh(self, created, endDate, refreshTime, stableRefreshTime=None):
        """
        Return whether an entry stored at `created` (ISO text) is still fresh.
        An entry whose data ends at `endDate` (ISO text, or None if unknown)
        more than the stable time ago lasts for stableRefreshTime, if given,
        and any other for refreshTime, both in seconds.
        """
        now = datetime.datetime.now()
        refresh = refreshTime
        if stableRefreshTime is not None and endDate is not None:
            if (now - datetime.datetime.fromisoformat(endDate)).total_seconds() > self.stableTime:
                refresh = stableRefreshTime
        return (now - datetime.datetime.fromisoformat(created)).total_seconds() < refresh

    def getCache(self, cacheName, refreshTime, stableRefreshTime = None, force=False):
        """Return a fresh lookup, or None on a miss."""
        if force:
            return None
        database = self.cache.connection
        if self.refresh and cacheName not in self.refreshed:
            self.refreshed.add(cacheName)
            with database:
                database.execute("DELETE FROM lookups WHERE key = ?", (cacheName,))
            return None
        row = database.execute("SELECT created, end_date, value FROM lookups WHERE key = ?", (cacheName,)).fetchone()
        if row is None:
            return None
        if self.isFresh(row[0], row[1], refreshTime, stableRefreshTime):
            return decode(row[2])
        with database:
            database.execute("DELETE FROM lookups WHERE key = ?", (cacheName,))
        return None

    def setCache(self, cacheName, data, endDate=None):
        """Store a lookup under its key."""
        with self.cache.connection:
            self.cache.connection.execute("INSERT OR REPLACE INTO lookups (key, created, end_date, value) VALUES (?, ?, ?, ?)",
                                          (cacheName, datetime.datetime.now().isoformat(), endDate, encode(data)))

    def readRecord(self, table, id, refreshTime=None, stableRefreshTime=None, complete=False):
        """
        Return the record with the given full OpenAlex ID from `table`, or None
        if it is not stored. If refreshTime is given, a record that is no longer
        fresh counts as not stored, and if `complete` is set, so does a search
        result whose author list was cut short.
        """
        if refreshTime is not None and self.refresh and (table, id) not in self.refreshed:
            self.refreshed.add((table, id))
            return None
        row = self.cache.connection.execute(f"SELECT fetched, end_date, truncated, record FROM {table} WHERE id = ?",
                                            (id,)).fetchone()
        if row is None:
            return None
        if complete and row[2]:
            return None
        if refreshTime is not None and not self.isFresh(row[0], row[1], refreshTime, stableRefreshTime):
            return None
        return decode(row[3])

    def storeRecord(self, record, truncated=False):
        """
        Store an OpenAlex record in the table for its kind, without committing.
        A search result whose author list was cut short does not replace a
        complete record.
        """
        table = tableFor(record['id'])
        database = self.cache.connection
        if truncated:
            row = database.execute(f"SELECT truncated FROM {table} WHERE id = ?", (record['id'],)).fetchone()
            if row is not None and not row[0]:
                return
        endDate = record.get('publication_date') or record.get('created_date')
        database.execute(f"INSERT OR REPLACE INTO {table} (id, fetched, end_date, truncated, record) VALUES (?, ?, ?, ?, ?)",
                         (record['id'], datetime.datetime.now().isoformat(), endDate, 1 if truncated else 0, encode(record)))

    def deleteRange(self, rangeId):
        """Remove a cached date range of a search and the list of what it returned, without committing."""
        self.cache.connection.execute("DELETE FROM search_results WHERE range_id = ?", (rangeId,))
        self.cache.connection.execute("DELETE FROM search_ranges WHERE id = ?", (rangeId,))

    def getRangeCache(self, cacheName, startDate, endDate, refreshTime,
                      stableRefreshTime=None, force=False):
        """Return fresh cached records for the request and the date ranges it does not cover."""
        if force:
            return [], [(startDate, endDate)]
        if self.refresh and cacheName not in self.refreshed:
            self.refreshed.add(cacheName)
            return [], [(startDate, endDate)]
        database = self.cache.connection
        row = database.execute("SELECT id FROM searches WHERE name = ?", (cacheName,)).fetchone()
        if row is None:
            return [], [(startDate, endDate)]

        fresh = []
        expired = []
        for rangeId, rangeStart, rangeEnd, created, stableDate in database.execute(
                "SELECT id, start_date, end_date, created, stable_date FROM search_ranges WHERE search_id = ?",
                (row[0],)).fetchall():
            if not self.isFresh(created, stableDate, refreshTime, stableRefreshTime):
                expired.append(rangeId)
                continue
            rangeStart = self.parseDate(rangeStart)
            rangeEnd = self.parseDate(rangeEnd)
            fresh.append((datetime.date.min if rangeStart is None else rangeStart,
                          datetime.date.max if rangeEnd is None else rangeEnd,
                          rangeId))
        if expired:
            with database:
                for rangeId in expired:
                    self.deleteRange(rangeId)

        lower = datetime.date.min if startDate is None else startDate
        upper = datetime.date.max if endDate is None else endDate
        fresh.sort(key=lambda item: item[0])
        need = lower
        used = []
        gaps = []
        for item in fresh:
            if item[0] > upper:
                break
            if item[1] < need:
                continue
            if item[0] > need:
                gaps.append((need, item[0] - datetime.timedelta(days=1)))
            used.append(item)
            if item[1] >= upper:
                need = None
                break
            need = item[1] + datetime.timedelta(days=1)
        if need is not None:
            gaps.append((need, upper))
        openGaps = []
        for gapStart, gapEnd in gaps:
            if gapStart == datetime.date.min:
                gapStart = None
            if gapEnd == datetime.date.max:
                gapEnd = None
            openGaps.append((gapStart, gapEnd))

        #The records of each range used, in the order OpenAlex returned them, each once
        results = []
        seen = set()
        for item in used:
            for (recordId,) in database.execute(
                    "SELECT record_id FROM search_results WHERE range_id = ? ORDER BY position", (item[2],)).fetchall():
                if recordId in seen:
                    continue
                seen.add(recordId)
                record = self.readRecord(tableFor(recordId), recordId)
                if record is not None:
                    results.append(record)
        return results, openGaps

    def setRangeCache(self, cacheName, data, startDate, endDate, stableDate=None):
        """
        Store the records a search returned and the date range they cover,
        replacing any cached ranges of the same search that lie inside it.
        """
        database = self.cache.connection
        with database:
            database.execute("INSERT OR IGNORE INTO searches (name) VALUES (?)", (cacheName,))
            searchId = database.execute("SELECT id FROM searches WHERE name = ?", (cacheName,)).fetchone()[0]
            for rangeId, oldStart, oldEnd in database.execute(
                    "SELECT id, start_date, end_date FROM search_ranges WHERE search_id = ?", (searchId,)).fetchall():
                oldStart = self.parseDate(oldStart)
                oldEnd = self.parseDate(oldEnd)
                if ((startDate is None or (oldStart is not None and startDate <= oldStart)) and
                        (endDate is None or (oldEnd is not None and oldEnd <= endDate))):
                    self.deleteRange(rangeId)
            rangeId = database.execute(
                "INSERT INTO search_ranges (search_id, start_date, end_date, created, stable_date) VALUES (?, ?, ?, ?, ?)",
                (searchId,
                 startDate.isoformat() if startDate is not None else None,
                 endDate.isoformat() if endDate is not None else None,
                 datetime.datetime.now().isoformat(),
                 stableDate.isoformat() if isinstance(stableDate, datetime.date) else stableDate)).lastrowid
            for position, record in enumerate(data):
                self.storeRecord(record, record.get('is_authors_truncated', False))
                database.execute("INSERT INTO search_results (range_id, position, record_id) VALUES (?, ?, ?)",
                                 (rangeId, position, record['id']))

    def searchCacheName(self, client, query, filter, dateFilter=None, mode="search"):
        """Build a cache key from a search and its non-range filters."""
        name = "search_" + mode + "_" + str(type(client)) + "_" + query
        dateKeys = set()
        if dateFilter is not None:
            _, startFilter, endFilter = self.dateFilterNames(dateFilter)
            dateKeys = {startFilter, endFilter}
        keys = sorted(key for key in filter if key not in dateKeys)
        for key in keys:
            name = name + "_" + key + "_" + str(filter[key])
        return name

    def parseDate(self, value):
        """Parse an ISO date bound, preserving None as an open bound."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime.date):
            return value
        return datetime.date.fromisoformat(str(value))

    def dateFilterNames(self, dateFilter):
        """Return the date field and its lower and upper filter names."""
        if len(dateFilter) != 3:
            raise ValueError("dateFilter must contain field, start, and end names")
        dateField, startFilter, endFilter = dateFilter
        return dateField, startFilter, endFilter

    def searchDateRange(self, filter, dateFilter):
        """Extract the requested start and end dates from search filters."""
        _, startFilter, endFilter = self.dateFilterNames(dateFilter)
        return (
            self.parseDate(filter.get(startFilter)),
            self.parseDate(filter.get(endFilter)),
        )

    def filterDateRange(self, results, dateFilter, startDate, endDate):
        """Restrict cached results to the requested date range."""
        dateField, _, _ = self.dateFilterNames(dateFilter)
        filtered = []
        for result in results:
            resultDate = self.parseDate(result.get(dateField))
            if resultDate is None:
                continue
            if startDate is not None and resultDate < startDate:
                continue
            if endDate is not None and resultDate > endDate:
                continue
            filtered.append(result)
        return filtered

    def getCacheName(self, client, query):
        """Build a cache key for an individual API object lookup."""
        name = "get_" + str(type(client)) + "_" + query
        return name

    def search(self, client, query, filter, per_page):
        """Create a paginated ordinary search request."""
        if len(filter)!=0:
            return client.search(query).filter(**filter).paginate(per_page=per_page, n_max=None)
        else:
            return client.search(query).paginate(per_page=per_page, n_max=None)

    def exact(self, client, query, filter, per_page):
        """Create a paginated exact search request."""
        if len(filter)!=0:
            return client.exact(query).filter(**filter).paginate(per_page=per_page, n_max=None)
        else:
            return client.exact(query).paginate(per_page=per_page, n_max=None)

    def filterOnly(self, client, filter, per_page):
        """Create a paginated request using only filters."""
        if len(filter)!=0:
            return client.filter(**filter).paginate(per_page=per_page, n_max=None)
        else:
            return client.paginate(per_page=per_page, n_max=None)

    def searchCount(self, client, query, filter, mode):
        """Return the number of results of a search, or None if search progress is not being reported."""
        if self.progress is None or (self.reportedStages is not None and "search" not in self.reportedStages):
            return None
        if mode == "exact":
            request = client.exact(query)
        elif mode == "filter":
            request = client
        else:
            request = client.search(query)
        if len(filter)!=0:
            request = request.filter(**filter)
        return request.count()

    def report(self, stage, done, total):
        """Pass progress to the progress callback, if one is set and the stage is being reported."""
        if self.progress is not None and (self.reportedStages is None or stage in self.reportedStages):
            self.progress(stage, done, total)

    def pages(self, client, query, filter, mode):
        """Create the paginated request for a search of the given mode: "search", "exact" or "filter"."""
        if mode == "exact":
            return self.exact(client, query, filter, self.defaultPerPage)
        if mode == "filter":
            return self.filterOnly(client, filter, self.defaultPerPage)
        return self.search(client, query, filter, self.defaultPerPage)

    def splitRange(self, startDate, endDate):
        """
        Return a date range (None for an open bound) as a list of pieces: two
        if it spans the stability boundary, so that the older, stable part can be
        cached separately from the recent part, and one otherwise.
        """
        boundary = (datetime.datetime.now() - datetime.timedelta(seconds=self.stableTime)).date()
        if (startDate is None or startDate <= boundary) and (endDate is None or endDate > boundary):
            return [(startDate, boundary), (boundary + datetime.timedelta(days=1), endDate)]
        return [(startDate, endDate)]

    def fetchRange(self, name, client, query, filter, dateFilter, mode, startDate, endDate):
        """
        Fetch the results of a search between startDate and endDate (inclusive,
        None for an open bound) and cache them. A range that spans the stability
        boundary is fetched and cached as two entries, so that the older, stable
        part is refreshed less often than the recent part.
        """
        _, startFilter, endFilter = self.dateFilterNames(dateFilter)
        pieces = self.splitRange(startDate, endDate)

        results = []
        for pieceStart, pieceEnd in pieces:
            pieceFilter = {}
            for key, value in filter.items():
                if key not in (startFilter, endFilter):
                    pieceFilter[key] = value
            if pieceStart is not None:
                pieceFilter[startFilter] = pieceStart.isoformat()
            if pieceEnd is not None:
                pieceFilter[endFilter] = pieceEnd.isoformat()
            fetched = []
            total = self.searchCount(client, query, pieceFilter, mode)
            for page in self.pages(client, query, pieceFilter, mode):
                fetched.extend(page)
                self.report("search", len(fetched), total)
            self.setRangeCache(name, fetched, pieceStart, pieceEnd, pieceFilter.get(endFilter, None))
            results.extend(fetched)
        return results

    def searchCore(self, query, client, filter, dateFilter=None):
        """Run an ordinary search, fetching only date ranges missing from the cache."""
        name = self.searchCacheName(client, query, filter, dateFilter)
        if dateFilter is not None:
            startDate, endDate = self.searchDateRange(filter, dateFilter)
            cached, gaps = self.getRangeCache(
                name, startDate, endDate, self.shortCache, self.longCache
            )
            if gaps and not self.fetchGaps:
                return self.fetchRange(name, client, query, filter, dateFilter, "search", startDate, endDate)
            results = self.filterDateRange(cached, dateFilter, startDate, endDate)
            for gapStart, gapEnd in gaps:
                results.extend(self.fetchRange(name, client, query, filter, dateFilter, "search", gapStart, gapEnd))
            self.report("search", len(results), len(results))
            return results
        cached = self.getCache(name,self.shortCache, self.longCache)
        if cached is not None:
            self.report("search", len(cached), len(cached))
            return cached
        results=[]
        i=0
        total = self.searchCount(client, query, filter, "search")
        for page in self.search(client, query, filter, self.defaultPerPage):
            results.extend(page)
            i=i+1
            self.report("search", len(results), total)
        self.setCache(name, results, filter.get(dateFilter,None))
        return results

    def searchCoreExact(self, query, client, filter, dateFilter=None):
        """Run an exact search, fetching only date ranges missing from the cache."""
        name = self.searchCacheName(client, query, filter, dateFilter, "exact")
        if dateFilter is not None:
            startDate, endDate = self.searchDateRange(filter, dateFilter)
            cached, gaps = self.getRangeCache(
                name, startDate, endDate, self.shortCache, self.longCache
            )
            if gaps and not self.fetchGaps:
                return self.fetchRange(name, client, query, filter, dateFilter, "exact", startDate, endDate)
            results = self.filterDateRange(cached, dateFilter, startDate, endDate)
            for gapStart, gapEnd in gaps:
                results.extend(self.fetchRange(name, client, query, filter, dateFilter, "exact", gapStart, gapEnd))
            self.report("search", len(results), len(results))
            return results
        cached = self.getCache(name,self.shortCache, self.longCache)
        if cached is not None:
            self.report("search", len(cached), len(cached))
            return cached
        results=[]
        i=0;
        total = self.searchCount(client, query, filter, "exact")
        for page in self.exact(client, query, filter, self.defaultPerPage):
            results.extend(page)
            i=i+1
            self.report("search", len(results), total)
        self.setCache(name, results, filter.get(dateFilter,None))
        return results


    def searchCoreFilter(self, client, filter, dateFilter=None):
        """Run a filter-only request, fetching only date ranges missing from the cache."""
        name = self.searchCacheName(client, "", filter, dateFilter, "filter")
        if dateFilter is not None:
            startDate, endDate = self.searchDateRange(filter, dateFilter)
            cached, gaps = self.getRangeCache(
                name, startDate, endDate, self.shortCache, self.longCache
            )
            if gaps and not self.fetchGaps:
                return self.fetchRange(name, client, "", filter, dateFilter, "filter", startDate, endDate)
            results = self.filterDateRange(cached, dateFilter, startDate, endDate)
            for gapStart, gapEnd in gaps:
                results.extend(self.fetchRange(name, client, "", filter, dateFilter, "filter", gapStart, gapEnd))
            self.report("search", len(results), len(results))
            return results
        cached = self.getCache(name,self.shortCache, self.longCache)
        if cached is not None:
            self.report("search", len(cached), len(cached))
            return cached
        results=[]
        i=0
        total = self.searchCount(client, "", filter, "filter")
        for page in self.filterOnly(client, filter, self.defaultPerPage):
            results.extend(page)
            i=i+1
            self.report("search", len(results), total)
        self.setCache(name, results, filter.get(dateFilter,None))
        return results

    def getCore(self, query, client, dateFilter=None):
        """
        Fetch an individual API object by any identifier OpenAlex accepts for
        it, such as a DOI, using the table of records for its kind. Which record
        an identifier names, or that it names none, is kept as a lookup.
        """
        table = CLIENT_TABLES[type(client)]
        name = "get_" + table + "_" + query
        recordId = self.getCache(name, self.shortCache, self.longCache)
        if name in self.cache:
            if recordId is None:
                return None
            record = self.readRecord(table, recordId, self.shortCache, self.longCache, True)
            if record is not None:
                return record
        try:
            result = client[query]
        except QueryError:
            print("Lookup failed for query:", query, file=sys.stderr)
            result = None
        if result is None:
            self.setCache(name, None)
            return None
        with self.cache.connection:
            self.storeRecord(result)
        self.setCache(name, result['id'], result.get(dateFilter, None))
        return result

    def setAPIKey(self, key):
        """Set the OpenAlex API key for requests."""
        config.api_key = key

    def searchWorks(self, query, filter={}):
        """Search works and cache results by publication-date range."""
        return self.searchCore(
            query, Works(), filter,
            ("publication_date", "from_publication_date", "to_publication_date")
        )
    
    def searchWorksExact(self, query, filter={}):
        """Perform an exact works search by publication-date range."""
        return self.searchCoreExact(
            query, Works(), filter,
            ("publication_date", "from_publication_date", "to_publication_date")
        )

    def filterWorks(self, filter={}):
        """Find works using only filters, cached by publication-date range."""
        return self.searchCoreFilter(
            Works(), filter,
            ("publication_date", "from_publication_date", "to_publication_date")
        )

    def filterWorksForAuthors(self, authorIds, from_date, to_date, stage=None):
        """
        Return the works of each of many authors, given by short OpenAlex ID,
        published between from_date and to_date (inclusive), keyed by author ID.
        Works not already cached are fetched for 10 authors at a time and cached
        for each author under the same key that a search for that author alone
        uses. Progress is reported in the given stage, as authors done out of
        authors asked for, and in the "works" stage as each batch's works
        arrive, or not at all if stage is None.
        """
        dateFilter = ("publication_date", "from_publication_date", "to_publication_date")
        startDate = self.parseDate(from_date)
        endDate = self.parseDate(to_date)
        names = {}
        found = {}
        #The date pieces missing from the cache, each with the authors missing it
        missing = {}
        remaining = {}
        for authorId in authorIds:
            filter = {"authorships.author.id": authorId, "from_publication_date": from_date, "to_publication_date": to_date}
            names[authorId] = self.searchCacheName(Works(), "", filter, dateFilter, "filter")
            cached, gaps = self.getRangeCache(names[authorId], startDate, endDate, self.shortCache, self.longCache)
            found[authorId] = self.filterDateRange(cached, dateFilter, startDate, endDate)
            remaining[authorId] = 0
            for gapStart, gapEnd in gaps:
                for piece in self.splitRange(gapStart, gapEnd):
                    missing.setdefault(piece, []).append(authorId)
                    remaining[authorId] = remaining[authorId] + 1

        done = 0
        for authorId in authorIds:
            if remaining[authorId] == 0:
                done = done + 1
        if stage is not None:
            self.report(stage, done, len(authorIds))

        for (pieceStart, pieceEnd), ids in missing.items():
            for start in range(0, len(ids), 10):
                chunk = ids[start:start + 10]
                pieceFilter = {"authorships.author.id": "|".join(chunk)}
                if pieceStart is not None:
                    pieceFilter["from_publication_date"] = pieceStart.isoformat()
                if pieceEnd is not None:
                    pieceFilter["to_publication_date"] = pieceEnd.isoformat()
                fetched = []
                total = self.searchCount(Works(), "", pieceFilter, "filter")
                #Progress is shown in the "works" stage as this chunk's works arrive, page by page
                if stage is not None and self.progress is not None:
                    total = Works().filter(**pieceFilter).count()
                for page in self.pages(Works(), "", pieceFilter, "filter"):
                    fetched.extend(page)
                    self.report("search", len(fetched), total)
                    #A batch reaching its total is not the end of the search, so that is left to the report of authors done
                    if stage is not None and (total is None or len(fetched) < total):
                        self.report("works", len(fetched), total)

                #Give each work to every author in this chunk who is among its authors
                works = {}
                for authorId in chunk:
                    works[authorId] = []
                for work in fetched:
                    #Search results list only the first authors of a large collaboration; a work's own record lists them all
                    if work.get('is_authors_truncated'):
                        full = self.getWork(work['id'].rsplit("/", 1)[-1])
                        if full is not None:
                            work = full
                    seen = set()
                    for authorship in work['authorships']:
                        otherId = authorship['author'].get('id')
                        if not otherId:
                            continue
                        shortId = otherId.rsplit("/", 1)[-1]
                        if shortId in works and shortId not in seen:
                            seen.add(shortId)
                            works[shortId].append(work)
                for authorId in chunk:
                    self.setRangeCache(names[authorId], works[authorId], pieceStart, pieceEnd,
                                       pieceFilter.get("to_publication_date", None))
                    found[authorId].extend(works[authorId])
                    remaining[authorId] = remaining[authorId] - 1
                    if remaining[authorId] == 0:
                        done = done + 1
                #All the authors being done is not the end of the search either; a tool may have more to fetch
                if stage is not None and done < len(authorIds):
                    self.report(stage, done, len(authorIds))
        return found

    def getWork(self, query):
        """Fetch one work by its OpenAlex identifier."""
        return self.getCore(query, Works(), "publication_date")

    def searchAuthor(self, query, filter={}):
        """Search authors with the ordinary search endpoint."""
        return self.searchCore(
            query, Authors(), filter,
            ("created_date", "from_created_date", "to_created_date")
        )

    def getAuthor(self, query):
        """Fetch one author by its OpenAlex identifier."""
        return self.getCore(query, Authors(), "created_date")

    def getAuthors(self, ids):
        """Fetch many authors by OpenAlex identifier, 100 per request, using the exact-key cache."""
        return self.getManyCore(Authors, ids, "created_date", None)

    def getWorks(self, ids, stage):
        """Fetch many works by OpenAlex identifier, 100 per request, using the exact-key cache.
        Progress is reported in the given stage, or not at all if it is None."""
        return self.getManyCore(Works, ids, "publication_date", stage)

    def earliestPublicationYear(self, authorId):
        """Return the publication year of an author's earliest work, or None if they have none, using the exact-key cache."""
        name = "earliest_" + authorId
        cached = self.getCache(name, self.longCache)
        if name in self.cache:
            return cached
        results = Works().filter(**{"authorships.author.id": authorId}).sort(publication_date="asc").get(per_page=1)
        year = results[0]['publication_year'] if results else None
        self.setCache(name, year)
        return year

    def autocompleteAuthors(self, query):
        """Return OpenAlex's author autocomplete suggestions for a name, using the exact-key cache."""
        name = "autocomplete_" + str(type(Authors())) + "_" + query
        cached = self.getCache(name, self.shortCache, self.longCache)
        if name in self.cache:
            return cached
        results = list(Authors().autocomplete(query))
        self.setCache(name, results)
        return results

    def autocompleteWorks(self, query):
        """Return OpenAlex's work autocomplete suggestions for a title, using the exact-key cache."""
        name = "autocomplete_" + str(type(Works())) + "_" + query
        cached = self.getCache(name, self.shortCache, self.longCache)
        if name in self.cache:
            return cached
        results = list(Works().autocomplete(query))
        self.setCache(name, results)
        return results

    def autocompleteInstitutions(self, query):
        """Return OpenAlex's institution autocomplete suggestions for a name, using the exact-key cache."""
        name = "autocomplete_" + str(type(Institutions())) + "_" + query
        cached = self.getCache(name, self.shortCache, self.longCache)
        if name in self.cache:
            return cached
        results = list(Institutions().autocomplete(query))
        self.setCache(name, results)
        return results

    def topicChildren(self, level, parentId):
        """
        Return the ID and name of each domain if level is "domain", or else of
        each field of a domain, subfield of a field or topic of a subfield,
        given by short OpenAlex ID, using the exact-key cache.
        """
        name = "children_" + level + "_" + parentId
        cached = self.getCache(name, self.longCache)
        if name in self.cache:
            return cached
        if level == "domain":
            request = Domains()
        elif level == "field":
            request = Fields().filter(**{"domain.id": parentId})
        elif level == "subfield":
            request = Subfields().filter(**{"field.id": parentId})
        else:
            request = Topics().filter(**{"subfield.id": parentId})
        results = []
        for page in request.paginate(per_page=self.defaultPerPage, n_max=None):
            #Only the ID and name are kept, as topic records are large
            for result in page:
                results.append({"id": result["id"], "display_name": result["display_name"]})
        self.setCache(name, results)
        return results

    def getTopicLevel(self, level, id):
        """Fetch one field, subfield or topic, as level says, by short OpenAlex ID, using the exact-key cache."""
        if level == "field":
            client = Fields()
        elif level == "subfield":
            client = Subfields()
        else:
            client = Topics()
        return self.getCore(id, client, "created_date")

    def searchInstitutions(self, query, filter={}):
        """Search institutions with the ordinary search endpoint."""
        return self.searchCore(
            query, Institutions(), filter,
            ("created_date", "from_created_date", "to_created_date")
        )

    def getInstitution(self, query):
        """Fetch one institution by its OpenAlex identifier."""
        return self.getCore(query, Institutions(), "created_date")

    def getManyCore(self, clientClass, ids, dateFilter, stage):
        """Fetch many API objects by OpenAlex identifier, full or short, 100 per request, using the table
        of records for their kind. Progress is reported in the given stage, or not at all if it is None."""
        table = CLIENT_TABLES[clientClass]
        found = {}
        missing = []
        for id in ids:
            fullId = id if id.startswith("https://") else "https://openalex.org/" + id
            record = self.readRecord(table, fullId, self.shortCache, self.longCache, True)
            if record is not None:
                found[id] = record
                continue
            #An identifier that names nothing is remembered, so that it is not asked for again
            missName = "missing_" + table + "_" + fullId
            self.getCache(missName, self.shortCache)
            if missName in self.cache:
                found[id] = None
            else:
                missing.append(id)

        for start in range(0, len(missing), 100):
            batch = {}
            for id in missing[start:start + 100]:
                batch[id.rsplit("/", 1)[-1]] = id
            results = clientClass().filter(openalex="|".join(batch)).get(per_page=100)
            returned = {}
            for result in results:
                returned[result["id"].rsplit("/", 1)[-1]] = result
            with self.cache.connection:
                for result in returned.values():
                    self.storeRecord(result)
            for shortId, id in batch.items():
                result = returned.get(shortId)
                if result is None:
                    fullId = id if id.startswith("https://") else "https://openalex.org/" + id
                    self.setCache("missing_" + table + "_" + fullId, None)
                found[id] = result
            if stage is not None:
                self.report(stage, min(start + 100, len(missing)), len(missing))
        if not missing and stage is not None:
            self.report(stage, len(found), len(found))
        return found

    def getInstitutions(self, ids):
        """Fetch many institutions by OpenAlex identifier, 100 per request, using the exact-key cache."""
        return self.getManyCore(Institutions, ids, "created_date", "institutions")

    def getFunders(self, ids):
        """Fetch many funders by OpenAlex identifier, 100 per request, using the exact-key cache."""
        return self.getManyCore(Funders, ids, "created_date", "funders")

    def searchKeywords(self, query, filter={}):
        """Search keywords with the ordinary search endpoint."""
        return self.searchCore(
            query, Keywords(), filter,
            ("created_date", "from_created_date", "to_created_date")
        )

    def getKeyword(self, query):
        """Fetch one keyword by its OpenAlex identifier."""
        return self.getCore(query, Keywords(), "created_date")
