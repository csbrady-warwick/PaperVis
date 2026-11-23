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

from pyalex_cache import pyalex_cache, QueryError
import csv
import sqlite3
import sys
import datetime
import argparse
import traceback
import requests

#Failures with a clear cause, reported to the user as a one-line message rather than a traceback
EXPECTED_ERRORS = (LookupError, OSError, QueryError, requests.exceptions.RequestException)

def describe_error(error):
    """
    Return a short description of an error for reporting to the user.
    """
    if isinstance(error, EXPECTED_ERRORS):
        return str(error)
    return f"{type(error).__name__}: {error}"

def report_errors_briefly():
    """
    Make an uncaught error with a clear cause end the program with a one-line
    message rather than a traceback. Other errors still show their traceback.
    """
    def report(errorType, error, errorTraceback):
        if isinstance(error, EXPECTED_ERRORS):
            print(f"Error: {error}", file=sys.stderr)
        else:
            traceback.print_exception(errorType, error, errorTraceback)
    sys.excepthook = report

def date_argument(text):
    """
    Check that a command line date is in YYYY-MM-DD format and return it unchanged.
    """
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a date in YYYY-MM-DD format")
    return text

def make_parser():
    """
    Build an argument parser with the options shared by all tools, and make
    errors with a clear cause report as a one-line message.
    """
    report_errors_briefly()
    parser = argparse.ArgumentParser()

    parser.add_argument("--from", dest="from_date", type=date_argument, default=(datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d"), help="From publication date in YYYY-MM-DD format. Default is 1 year ago.")
    parser.add_argument("--to", dest="to_date", type=date_argument, default=datetime.datetime.now().strftime("%Y-%m-%d"), help="To publication date in YYYY-MM-DD format. Default is today.")
    parser.add_argument("--use_cache", dest="use_cache", type=int, default=1, help="Use cache. 1 to use cache, 0 to not use cache. Default is 1.")
    parser.add_argument("--output", dest="output_file", help="Output filename. Default is %(default)s.")
    parser.add_argument("--apikey", dest="apikey", default=None, help="OpenAlex API key. Default is no key.")
    parser.add_argument("--cache_file", dest="cache_file", default="cache.db", help="Filename of the cache. Default is cache.db.")
    parser.add_argument("--refresh", dest="refresh", type=int, default=0, help="Fetch everything afresh from OpenAlex, replacing what is in the cache. 1 to refresh, 0 to use the cache as normal. Default is 0.")
    return parser

CHECKBOX = "checkbox"

LEVELS = ["topic", "subfield", "field", "domain"]

#Each tool option is described once and used for both the command line and the dashboard:
# name, dashboard label, command line help, default, type, and a list of choices, CHECKBOX or None.
# An option whose label is None is only offered on the command line, and one whose help is None only on the dashboard.
LEVEL_OPTION = {"name": "level", "label": "Level",
                "help": "Topic level to group by: topic, subfield, field or domain. Default is topic.",
                "default": "topic", "type": str, "choices": LEVELS}
ALL_TOPICS_OPTION = {"name": "all_topics", "label": "Use all topics",
                     "help": "Use all of a work's topics. 1 to use all topics, 0 to use only the primary topic. Default is 0.",
                     "default": 0, "type": int, "choices": CHECKBOX}
MIN_WORKS_OPTION = {"name": "min_works", "label": "Minimum works for a pin on the map",
                    "help": "Institutions with fewer works than this are not pinned on the map. Default is 2.",
                    "default": 2, "type": int, "choices": None}

def add_options(parser, options):
    """
    Add a command line option for each option description.
    """
    for option in options:
        if option["help"] is None:
            continue
        parser.add_argument(f"--{option['name']}", dest=option["name"], type=option["type"],
                            default=option["default"], help=option["help"])

def open_cache(args):
    """
    Create a pyalex_cache, loading the cache file and setting the API key as requested.
    """
    c=pyalex_cache()
    if args.use_cache:
        try:
            c.loadCache(args.cache_file)
        except (OSError, EOFError, ValueError, sqlite3.DatabaseError) as error:
            raise OSError(f"Could not read the cache file '{args.cache_file}' ({error}). "
                          f"Delete it, or choose another with --cache_file.") from error
    if args.apikey:
        c.setAPIKey(args.apikey)
    #Only the command line tools have --refresh; the dashboard sets refresh for each search itself
    c.refresh = getattr(args, "refresh", 0) == 1
    return c

def write_table(path, header, rows):
    """
    Write a table as CSV.
    """
    with open(path, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"Table written to {path}")
