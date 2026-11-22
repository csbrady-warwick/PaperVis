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
import gzip
import sqlite3
import zlib

class CacheStore:
    """
    The cache's entries, used like a dictionary but kept in an SQLite database.
    An entry is only read and decoded when it is first asked for, and changes
    are held in memory until save is called, when only they are written.
    """

    def __init__(self):
        self.connection = None
        self.loaded = {}
        self.dirty = set()
        self.removed = set()

    def open(self, filename):
        """Open the database, creating it if it does not exist."""
        #The dashboard's searches run in their own threads, one at a time
        self.connection = sqlite3.connect(filename, check_same_thread=False)
        self.connection.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB)")

    def read(self, key):
        """Return whether an entry exists, and its value, reading it from the database if need be."""
        if key in self.removed:
            return False, None
        if key in self.loaded:
            return True, self.loaded[key]
        if self.connection is None:
            return False, None
        row = self.connection.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        if row is None:
            return False, None
        value = json.loads(zlib.decompress(row[0]))
        self.loaded[key] = value
        return True, value

    def __contains__(self, key):
        found, value = self.read(key)
        return found

    def __getitem__(self, key):
        found, value = self.read(key)
        if not found:
            raise KeyError(key)
        return value

    def get(self, key, default=None):
        found, value = self.read(key)
        if not found:
            return default
        return value

    def __setitem__(self, key, value):
        self.loaded[key] = value
        self.dirty.add(key)
        self.removed.discard(key)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        self.loaded.pop(key, None)
        self.dirty.discard(key)
        self.removed.add(key)

    def pop(self, key, default=None):
        found, value = self.read(key)
        if not found:
            return default
        del self[key]
        return value

    def __iter__(self):
        keys = set(self.loaded)
        if self.connection is not None:
            for (key,) in self.connection.execute("SELECT key FROM cache"):
                keys.add(key)
        keys = keys - self.removed
        return iter(list(keys))

    def update(self, other):
        for key, value in other.items():
            self[key] = value

    def save(self):
        """Write the entries changed or removed since the last save to the database."""
        with self.connection:
            for key in self.removed:
                self.connection.execute("DELETE FROM cache WHERE key = ?", (key,))
            for key in self.dirty:
                value = zlib.compress(json.dumps(self.loaded[key]).encode())
                self.connection.execute("INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)", (key, value))
        self.dirty = set()
        self.removed = set()

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
        #Set whenever the cache is changed after loading, so that an unchanged cache is not saved again
        self.changed = False
        self.cache=CacheStore()
        self.shortCache=datetime.timedelta(hours=1).total_seconds()
        self.longCache = datetime.timedelta(days=30).total_seconds()
        self.stableTime = datetime.timedelta(days=100).total_seconds()

    def loadCache(self, filename):
        """Open the cache database, creating it if it does not exist."""
        self.cache.open(filename)

    def saveCache(self, filename, force=False):
        """Write the cache entries changed since the last save to the database, if any have changed or force is set."""
        if not self.changed and not force:
            return
        self.cache.save()
        self.changed = False

    def getCache(self, cacheName, refreshTime, stableRefreshTime = None, force=False):
        """Return a fresh exact-key cache entry, or None on a miss."""
        if force:
            return None
        if self.refresh and cacheName not in self.refreshed:
            self.refreshed.add(cacheName)
            if cacheName in self.cache:
                del self.cache[cacheName]
                self.changed = True
            return None
        if cacheName not in self.cache:
            return None
        co = self.cache[cacheName]
        time = datetime.datetime.fromisoformat(co[0])
        srf = stableRefreshTime
        if stableRefreshTime == None: srf = refreshTime

        stable = False
        endDate = None
        if co[1] is not None:
            endDate = datetime.datetime.fromisoformat(co[1])
        if endDate is not None:
            if (datetime.datetime.now() - endDate).total_seconds() > self.stableTime:
                stable=True

        rt = refreshTime
        if stable: rt = srf

        if (datetime.datetime.now() - time).total_seconds() < rt:
            return co[2]
        del self.cache[cacheName]
        self.changed = True
        return None

    def getRangeCache(self, cacheName, startDate, endDate, refreshTime,
                      stableRefreshTime=None, force=False):
        """Return fresh cached data for the request and the date ranges it does not cover."""
        if force:
            return [], [(startDate, endDate)]
        if self.refresh and cacheName not in self.refreshed:
            self.refreshed.add(cacheName)
            return [], [(startDate, endDate)]
        entries = self.cache.get(cacheName, [])
        if not isinstance(entries, list) or (entries and not isinstance(entries[0], dict)):
            return [], [(startDate, endDate)]

        now = datetime.datetime.now()
        kept = []
        fresh = []
        for entry in entries:
            time = datetime.datetime.fromisoformat(entry["created"])
            stable = False
            stableDate = entry.get("stable_date")
            if stableDate is not None:
                stable = (now -
                          datetime.datetime.fromisoformat(stableDate)).total_seconds() > self.stableTime

            refresh = refreshTime
            if stableRefreshTime is not None and stable:
                refresh = stableRefreshTime
            if (now - time).total_seconds() >= refresh:
                continue
            kept.append(entry)

            entryStart = self.parseDate(entry.get("start"))
            entryEnd = self.parseDate(entry.get("end"))
            fresh.append((datetime.date.min if entryStart is None else entryStart,
                          datetime.date.max if entryEnd is None else entryEnd,
                          entry["data"]))
        if len(kept) != len(entries):
            self.changed = True
        if kept:
            self.cache[cacheName] = kept
        else:
            self.cache.pop(cacheName, None)

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

        results = []
        seen = set()
        for item in used:
            for result in item[2]:
                if result["id"] in seen:
                    continue
                seen.add(result["id"])
                results.append(result)
        return results, openGaps

    def setRangeCache(self, cacheName, data, startDate, endDate, stableDate=None):
        """Store data and the date range it covers."""
        entry = {
            "created": datetime.datetime.now().isoformat(),
            "start": startDate.isoformat() if startDate is not None else None,
            "end": endDate.isoformat() if endDate is not None else None,
            "stable_date": stableDate.isoformat() if isinstance(stableDate, datetime.date) else stableDate,
            "data": data,
        }
        entries = self.cache.get(cacheName, [])
        if not isinstance(entries, list) or (entries and not isinstance(entries[0], dict)):
            entries = []
        kept = []
        for oldEntry in entries:
            oldStart = self.parseDate(oldEntry.get("start"))
            oldEnd = self.parseDate(oldEntry.get("end"))
            if ((startDate is None or (oldStart is not None and startDate <= oldStart)) and
                    (endDate is None or (oldEnd is not None and oldEnd <= endDate))):
                continue
            kept.append(oldEntry)
        entries = kept
        entries.append(entry)
        self.cache[cacheName] = entries
        self.changed = True

    def coalesceCache(self, minRemaining):
        """Combine overlapping stable date-range entries with at least minRemaining seconds before expiry."""
        now = datetime.datetime.now()
        for cacheName in list(self.cache):
            entries = self.cache[cacheName]
            if not isinstance(entries, list) or not entries or not isinstance(entries[0], dict):
                continue

            kept = []
            mergeable = []
            for entry in entries:
                time = datetime.datetime.fromisoformat(entry["created"])
                stable = False
                stableDate = entry.get("stable_date")
                if stableDate is not None:
                    stable = (now -
                              datetime.datetime.fromisoformat(stableDate)).total_seconds() > self.stableTime

                refresh = self.longCache if stable else self.shortCache
                remaining = refresh - (now - time).total_seconds()
                if remaining <= 0:
                    continue
                if not stable or remaining < minRemaining:
                    kept.append(entry)
                    continue

                entryStart = self.parseDate(entry.get("start"))
                entryEnd = self.parseDate(entry.get("end"))
                mergeable.append((datetime.date.min if entryStart is None else entryStart,
                                  datetime.date.max if entryEnd is None else entryEnd,
                                  entry))
            if not kept and not mergeable:
                del self.cache[cacheName]
                self.changed = True
                continue

            mergeable.sort(key=lambda item: item[0])
            combined = []
            for entryStart, entryEnd, entry in mergeable:
                if combined and entryStart <= combined[-1][1]:
                    lastStart, lastEnd, last = combined[-1]
                    seen = set()
                    for result in last["data"]:
                        seen.add(result["id"])
                    data = list(last["data"])
                    for result in entry["data"]:
                        if result["id"] not in seen:
                            data.append(result)
                    if entryEnd > lastEnd:
                        lastEnd = entryEnd
                        stableDate = entry["stable_date"]
                    else:
                        stableDate = last["stable_date"]
                    combined[-1] = (lastStart, lastEnd, {
                        "created": min(last["created"], entry["created"]),
                        "start": last["start"],
                        "end": None if lastEnd == datetime.date.max else lastEnd.isoformat(),
                        "stable_date": stableDate,
                        "data": data,
                    })
                else:
                    combined.append((entryStart, entryEnd, entry))
            for item in combined:
                kept.append(item[2])
            if len(kept) != len(entries):
                self.changed = True
            self.cache[cacheName] = kept

    def setCache(self, cacheName, data, endDate=None):
        """Store data under an exact cache key."""
        self.cache[cacheName] = [datetime.datetime.now().isoformat(), endDate, data]
        self.changed = True

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
        """Fetch an individual API object, using the exact-key cache."""
        name = self.getCacheName(client, query)
        cached = self.getCache(name, self.shortCache, self.longCache)
        if name in self.cache:
            return cached
        try:
            result = client[query]
        except QueryError:
            print("Lookup failed for query:", query, file=sys.stderr)
            result = None
        endDate = result.get(dateFilter, None) if result is not None else None
        self.setCache(name, result, endDate)
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
        """Fetch many API objects by OpenAlex identifier, 100 per request, using the exact-key cache.
        Progress is reported in the given stage, or not at all if it is None."""
        client = clientClass()
        found = {}
        missing = []
        for id in ids:
            name = self.getCacheName(client, id)
            cached = self.getCache(name, self.shortCache, self.longCache)
            if name in self.cache:
                found[id] = cached
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
            for shortId, id in batch.items():
                result = returned.get(shortId)
                endDate = result.get(dateFilter, None) if result is not None else None
                self.setCache(self.getCacheName(client, id), result, endDate)
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
