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

from openalex_cli import open_cache, report_errors_briefly
import argparse

if __name__ == "__main__":
    report_errors_briefly()

    #Get command line arguments
    # 1 positional argument is the name, or start of the name, of the author
    # keyword arguments are
    # 1) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 2) apikey - The OpenAlex API key. default is no key
    # 3) cache_file - The filename of the cache. default is cache.db

    #Parse keyword arguments using argparse
    parser = argparse.ArgumentParser()

    #Positional argument for the name
    parser.add_argument("name", help="Name, or start of the name, of the author. Example: 'yoshua bengio'")

    parser.add_argument("--use_cache", dest="use_cache", type=int, default=1, help="Use cache. 1 to use cache, 0 to not use cache. Default is 1.")
    parser.add_argument("--apikey", dest="apikey", default=None, help="OpenAlex API key. Default is no key.")
    parser.add_argument("--cache_file", dest="cache_file", default="cache.db", help="Filename of the cache. Default is cache.db.")
    parser.add_argument("--refresh", dest="refresh", type=int, default=0, help="Fetch the suggestions afresh from OpenAlex, replacing what is in the cache. 1 to refresh, 0 to use the cache as normal. Default is 0.")
    args = parser.parse_args()

    c = open_cache(args)

    candidates = c.autocompleteAuthors(args.name)
    if args.use_cache:
        c.saveCache(args.cache_file)

    for candidate in candidates:
        print(f"{candidate['id'].rsplit('/', 1)[-1]}  {candidate['display_name']}")
        print(f"    {candidate.get('hint') or ''}  works: {candidate.get('works_count')}  ORCID: {candidate.get('external_id') or 'none'}")
