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

from openalex_cli import make_parser

def make_author_parser():
    """
    Build an argument parser for tools that work from a single author: the
    options shared by all tools and the author's identifier.
    """
    parser = make_parser()

    #Positional argument for the author
    parser.add_argument("author", help="OpenAlex author ID, for example A5023888391, or ORCID, for example 0000-0002-1825-0097")
    return parser
