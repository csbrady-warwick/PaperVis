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
from utils import narrowest_topic

def make_institution_parser():
    """
    Build an argument parser for tools that work from a single institution:
    the options shared by all tools, the institution's identifier and the
    field, subfield or topic that its works are chosen from.
    """
    parser = make_parser()

    #Positional argument for the institution
    parser.add_argument("institution", help="OpenAlex institution ID, for example I39555362, or ROR ID")
    #Exactly one of the field, subfield or topic must be given
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--field", dest="field", help="OpenAlex ID of the field, for example 17")
    group.add_argument("--subfield", dest="subfield", help="OpenAlex ID of the subfield")
    group.add_argument("--topic", dest="topic", help="OpenAlex ID of the topic")
    return parser

def topic_choice(args):
    """
    Return the level, "field", "subfield" or "topic", and the ID given on the command line.
    """
    return narrowest_topic(args.field, args.subfield, args.topic)
