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

def make_paper_parser():
    """
    Build an argument parser for tools that work from a single paper: the
    options shared by all tools and the paper's DOI.
    """
    parser = make_parser()

    #Positional argument for the DOI
    parser.add_argument("doi", help="DOI of the paper, with or without https://doi.org/, or its OpenAlex work ID, for example W2741809807")
    return parser
