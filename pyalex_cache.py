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

import json
import sys
import datetime
import gzip

class pyalex_cache:

    def __init__(self):
        """Initialize cache storage and refresh intervals."""
        self.defaultPerPage=200
        self.cache={}
        self.shortCache=datetime.timedelta(hours=1).total_seconds()
        self.longCache = datetime.timedelta(days=30).total_seconds()
        self.stableTime = datetime.timedelta(days=100).total_seconds()

    def loadCache(self, filename):
        """Load cached entries from a gzip-compressed JSON file."""
        try:
            with gzip.open(filename, 'rt') as file:
                cacheIn = json.load(file)
        except FileNotFoundError:
            return
        if not isinstance(cacheIn, dict):
            raise ValueError("cache file must contain a JSON object")
        self.cache.update(cacheIn)

    def saveCache(self, filename):
        """Save cached entries to a gzip-compressed JSON file."""
        with gzip.open(filename, 'wt') as file:
            json.dump(self.cache, file)

    def getCache(self, cacheName, refreshTime, stableRefreshTime = None, force=False):
        """Return a fresh exact-key cache entry, or None on a miss."""
        if force:
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
        return None

    def getRangeCache(self, cacheName, startDate, endDate, refreshTime,
                      stableRefreshTime=None, force=False):
        """Return a fresh cached entry whose date range contains the request."""
        if force:
            return None
        entries = self.cache.get(cacheName, [])
        if not isinstance(entries, list) or (entries and not isinstance(entries[0], dict)):
            return None

        for entry in entries:
            entryStart = self.parseDate(entry.get("start"))
            entryEnd = self.parseDate(entry.get("end"))
            if entryStart is not None and (startDate is None or entryStart > startDate):
                continue
            if entryEnd is not None and (endDate is None or entryEnd < endDate):
                continue

            time = datetime.datetime.fromisoformat(entry["created"])
            stable = False
            stableDate = entry.get("stable_date")
            if stableDate is not None:
                stable = (datetime.datetime.now() -
                          datetime.datetime.fromisoformat(stableDate)).total_seconds() < self.stableTime

            refresh = refreshTime
            if stableRefreshTime is not None and stable:
                refresh = stableRefreshTime
            if (datetime.datetime.now() - time).total_seconds() < refresh:
                return entry["data"]
        return None

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
        entries.append(entry)
        self.cache[cacheName] = entries

    def setCache(self, cacheName, data, endDate=None):
        """Store data under an exact cache key."""
        self.cache[cacheName] = [datetime.datetime.now().isoformat(), endDate, data]

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
        return [
            result for result in results
            for resultDate in [self.parseDate(result.get(dateField))]
            if resultDate is not None
            and (startDate is None or startDate <= resultDate)
            and (endDate is None or resultDate <= endDate)
        ]

    def getCacheName(self, client, query):
        """Build a cache key for an individual API object lookup."""
        name = "get_" + str(type(client)) + "_" + query
        return name

    def search(self, client, query, filter, per_page):
        """Create a paginated ordinary search request."""
        if len(filter)!=0:
            return client.search(query).filter(**filter).paginate(per_page=per_page)
        else:
            return client.search(query).paginate(per_page=per_page)

    def exact(self, client, query, filter, per_page):
        """Create a paginated exact search request."""
        if len(filter)!=0:
            return client.exact(query).filter(**filter).paginate(per_page=per_page)
        else:
            return client.exact(query).paginate(per_page=per_page)

    def searchCore(self, query, client, filter, dateFilter=None):
        """Run an ordinary search, using an exact or containing cache entry."""
        name = self.searchCacheName(client, query, filter, dateFilter)
        if dateFilter is not None:
            startDate, endDate = self.searchDateRange(filter, dateFilter)
            cached = self.getRangeCache(
                name, startDate, endDate, self.shortCache, self.longCache
            )
            if cached is not None:
                return self.filterDateRange(cached, dateFilter, startDate, endDate)
        else:
            cached = self.getCache(name,self.shortCache, self.longCache)
            if cached is not None:
                return cached
        results=[]
        i=0
        for page in self.search(client, query, filter, self.defaultPerPage):
            results.extend(page)
            i=i+1
        if dateFilter is not None:
            _, _, endFilter = self.dateFilterNames(dateFilter)
            self.setRangeCache(name, results, startDate, endDate,
                               filter.get(endFilter, None))
        else:
            self.setCache(name, results, filter.get(dateFilter,None))
        return results

    def searchCoreExact(self, query, client, filter, dateFilter=None):
        """Run an exact search, using an exact or containing cache entry."""
        name = self.searchCacheName(client, query, filter, dateFilter, "exact")
        if dateFilter is not None:
            startDate, endDate = self.searchDateRange(filter, dateFilter)
            cached = self.getRangeCache(
                name, startDate, endDate, self.shortCache, self.longCache
            )
            if cached is not None:
                return self.filterDateRange(cached, dateFilter, startDate, endDate)
        else:
            cached = self.getCache(name,self.shortCache, self.longCache)
            if cached is not None:
                return cached
        results=[]
        i=0;
        for page in self.exact(client, query, filter, self.defaultPerPage):
            results.extend(page)
            i=i+1
        if dateFilter is not None:
            _, _, endFilter = self.dateFilterNames(dateFilter)
            self.setRangeCache(name, results, startDate, endDate,
                               filter.get(endFilter, None))
        else:
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

    def searchInstitutions(self, query, filter={}):
        """Search institutions with the ordinary search endpoint."""
        return self.searchCore(
            query, Institutions(), filter,
            ("created_date", "from_created_date", "to_created_date")
        )

    def getInstitution(self, query):
        """Fetch one institution by its OpenAlex identifier."""
        return self.getCore(query, Institutions(), "created_date")

    def searchKeywords(self, query, filter={}):
        """Search keywords with the ordinary search endpoint."""
        return self.searchCore(
            query, Keywords(), filter,
            ("created_date", "from_created_date", "to_created_date")
        )

    def getKeyword(self, query):
        """Fetch one keyword by its OpenAlex identifier."""
        return self.getCore(query, Keywords(), "created_date")
