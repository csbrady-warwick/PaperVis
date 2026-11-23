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

from openalex_cli import CHECKBOX, open_cache, describe_error, report_errors_briefly
from utils import topic_names, author_works, narrowest_topic, topic_name
from dashboard_html import RENDERERS
import FieldPie
import MapSearch
import LongTail
import FieldGrowth
import CountrySearch
import FunderSearch
import CitationStats
import VenueSearch
import TopicPairs
import InstitutionTypes
import PaperList
import KeywordAuthors
import OpenAccess
import WorkTypes
import InternationalCollaboration
import TeamSize
import CitingPapers
import References
import CoCited
import PaperAuthors
import CitingFields
import CitingLongTail
import CitingAuthors
import CitationTimeline
import CitingInstitutions
import CitingCountries
import SelfCitations
import CitingVenues
import CitingInstitutionTypes
import AuthorPublications
import AuthorFields
import CoAuthors
import CoAuthorMap
import CoAuthorCountries
import CoAuthorNetwork
import PossibleReviewers
import AuthorContact
import AuthorVenues
import AuthorOutput
import AuthorCitations
import AuthorSummary
import AuthorTopPapers
import WhoCitesThem
import WhoTheyCite
import AffiliationHistory
import AuthorFunders
import InstitutionWorks
import InstitutionSummary
import InstitutionOutput
import InstitutionBreakdown
import InstitutionFunders
import InstitutionVenues
import InstitutionPartners
import InstitutionCountries
import InstitutionNetwork
import InstitutionCollaborators
import InstitutionAuthors
import CitingOpenAccess
import CitingWorkTypes
import CitingTeamSize
import CitingInternational
import AuthorOpenAccess
import AuthorWorkTypes
import AuthorTeamSize
import AuthorInternational
import InstitutionOpenAccess
import InstitutionWorkTypes
import InstitutionTeamSize
import InstitutionInternational
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, urlencode
from http.cookies import SimpleCookie
import argparse
import datetime
import hmac
import html
import secrets
import json
import os
import threading
import time
import traceback
from plotly.offline import get_plotlyjs

#The tools offered by the dashboard, in the order they are listed
TOOLS = [
    FieldPie.TOOL,
    MapSearch.TOOL,
    LongTail.TOOL,
    FieldGrowth.TOOL,
    CountrySearch.TOOL,
    FunderSearch.TOOL,
    CitationStats.TOOL,
    VenueSearch.TOOL,
    TopicPairs.TOOL,
    InstitutionTypes.TOOL,
    PaperList.TOOL,
    KeywordAuthors.TOOL,
    OpenAccess.TOOL,
    WorkTypes.TOOL,
    InternationalCollaboration.TOOL,
    TeamSize.TOOL,
    PaperAuthors.TOOL,
    CitingPapers.TOOL,
    References.TOOL,
    CoCited.TOOL,
    CitingFields.TOOL,
    CitingLongTail.TOOL,
    CitingAuthors.TOOL,
    CitationTimeline.TOOL,
    CitingInstitutions.TOOL,
    CitingCountries.TOOL,
    SelfCitations.TOOL,
    CitingVenues.TOOL,
    CitingInstitutionTypes.TOOL,
    CitingOpenAccess.TOOL,
    CitingWorkTypes.TOOL,
    CitingTeamSize.TOOL,
    CitingInternational.TOOL,
    AuthorContact.TOOL,
    AuthorSummary.TOOL,
    AuthorPublications.TOOL,
    AuthorFields.TOOL,
    CoAuthors.TOOL,
    CoAuthorMap.TOOL,
    CoAuthorCountries.TOOL,
    CoAuthorNetwork.TOOL,
    PossibleReviewers.TOOL,
    AuthorVenues.TOOL,
    AuthorOutput.TOOL,
    AuthorCitations.TOOL,
    AuthorTopPapers.TOOL,
    WhoCitesThem.TOOL,
    WhoTheyCite.TOOL,
    AffiliationHistory.TOOL,
    AuthorFunders.TOOL,
    AuthorOpenAccess.TOOL,
    AuthorWorkTypes.TOOL,
    AuthorTeamSize.TOOL,
    AuthorInternational.TOOL,
    InstitutionWorks.TOOL,
    InstitutionSummary.TOOL,
    InstitutionOutput.TOOL,
    InstitutionBreakdown.TOOL,
    InstitutionFunders.TOOL,
    InstitutionVenues.TOOL,
    InstitutionPartners.TOOL,
    InstitutionCountries.TOOL,
    InstitutionNetwork.TOOL,
    InstitutionCollaborators.TOOL,
    InstitutionAuthors.TOOL,
    InstitutionOpenAccess.TOOL,
    InstitutionWorkTypes.TOOL,
    InstitutionTeamSize.TOOL,
    InstitutionInternational.TOOL,
]

TOOLS_BY_NAME = {}
for tool in TOOLS:
    TOOLS_BY_NAME[tool["name"]] = tool

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

#Files served from STATIC_DIR: URL path, filename and content type
STATIC_FILES = {
    "/dashboard.css": ("dashboard.css", "text/css"),
    "/dashboard.js": ("dashboard.js", "application/javascript"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}

def tools_for(kind):
    """
    Return the tools that take the given kind of input, "search" or "paper".
    """
    tools = []
    for tool in TOOLS:
        if tool["input"] == kind:
            tools.append(tool)
    return tools

def dashboard_options(tool):
    """
    Return the options of a tool that are shown on the dashboard.
    """
    options = []
    for option in tool["options"]:
        if option["label"]:
            options.append(option)
    return options

def default_form():
    """
    Return the form values shown before any search.
    """
    form = {
        "mode": "search",
        "tool": "pie",
        "search_term": "",
        "doi": "",
        "author": "",
        "institution": "",
        "domain": "",
        "field": "",
        "subfield": "",
        "topic": "",
        "refresh": "0",
        "from_date": (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
        "to_date": datetime.datetime.now().strftime("%Y-%m-%d"),
    }
    for tool in TOOLS:
        for option in dashboard_options(tool):
            form[f"{tool['name']}_{option['name']}"] = str(option["default"])
    return form

def read_form(query):
    """
    Return the form values in a URL query, with defaults for any not given.
    """
    #A checkbox sends its hidden 0 then, if ticked, 1, so use the last value of each field
    form = default_form()
    for key, values in parse_qs(query).items():
        form[key] = values[-1]
    return form

def run_tool(c, form):
    """
    Run the selected tool and return its results as HTML.
    """
    tool = TOOLS_BY_NAME[form["tool"]]
    if tool["input"] == "paper":
        value = form["doi"]
    elif tool["input"] == "author":
        value = form["author"]
    elif tool["input"] == "institution":
        value = form["institution"]
    else:
        value = form["search_term"]
    options = {}
    for option in dashboard_options(tool):
        options[option["name"]] = option["type"](form[f"{tool['name']}_{option['name']}"])
    if tool["input"] == "institution":
        #The narrowest of the field, subfield and topic chosen selects the works
        options["topic_level"], options["topic_id"] = narrowest_topic(form["field"], form["subfield"], form["topic"])
        options["topic_name"] = topic_name(c, options["topic_level"], options["topic_id"])

    views = tool["views"](c, value, form["from_date"], form["to_date"], options)
    result = ""
    for view in views:
        #Renderers that link to other searches keep the dates of the search that produced the view
        view["query"] = form
        result = result + RENDERERS[view["kind"]](view)
    return result

def tool_controls(tools, form):
    """
    Return the tool selector and each tool's options for one tab's form.
    """
    toolOptions = ""
    for tool in tools:
        if tool["name"] == form["tool"]:
            selected = " selected"
        else:
            selected = ""
        toolOptions = toolOptions + f"<option value=\"{tool['name']}\"{selected}>{html.escape(tool['label'])}</option>"

    fieldsets = ""
    for tool in tools:
        fields = ""
        for option in dashboard_options(tool):
            name = option["name"]
            label = option["label"]
            choices = option["choices"]
            key = f"{tool['name']}_{name}"
            if choices == CHECKBOX:
                #An unticked checkbox is not sent, so the hidden input sends 0 instead
                field = (f"<input type=\"hidden\" name=\"{key}\" value=\"0\">"
                         f"<input type=\"checkbox\" name=\"{key}\" value=\"1\"{' checked' if form[key] == '1' else ''}>")
            elif choices:
                choiceOptions = ""
                for choice in choices:
                    if choice == form[key]:
                        selected = " selected"
                    else:
                        selected = ""
                    choiceOptions = choiceOptions + f"<option{selected}>{html.escape(choice)}</option>"
                field = f"<select name=\"{key}\">{choiceOptions}</select>"
            elif option.get("suggest"):
                #A box with suggestions that the page fills in, while still allowing any text
                field = (f"<input name=\"{key}\" value=\"{html.escape(form[key])}\" list=\"{key}_list\" "
                         f"data-suggest=\"{option['suggest']}\" autocomplete=\"off\"><datalist id=\"{key}_list\"></datalist>")
            else:
                field = f"<input name=\"{key}\" value=\"{html.escape(form[key])}\">"
            if choices == CHECKBOX:
                fields = fields + f"<label class=\"check\">{field} {html.escape(label)}</label>"
            else:
                fields = fields + f"<label>{html.escape(label)} {field}</label>"
        if fields:
            fieldsets = fieldsets + f"<fieldset data-tool=\"{tool['name']}\"><legend>Options</legend>{fields}</fieldset>"

    return f"<label>Tool <select name=\"tool\">{toolOptions}</select></label>{fieldsets}"

def page(form, result):
    """
    Return the dashboard page with the forms filled in from `form` and the
    results of the last search below them.
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PaperVis</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<script src="/plotly.js"></script>
<link rel="stylesheet" href="/dashboard.css">
</head>
<body>
<header><h1><a href="/">PaperVis</a></h1><p>Visualizing research with OpenAlex</p></header>
<div class="layout">
<aside class="panel" data-mode="{html.escape(form['mode'])}">
<div class="tabs">
<button type="button" data-mode="search">Keyword</button>
<button type="button" data-mode="paper">Paper</button>
<button type="button" data-mode="author">Author</button>
<button type="button" data-mode="institution">Institution</button>
</div>
<form class="toolform" data-mode="search" method="get" action="/">
<input type="hidden" name="mode" value="search">
<label>Search term <input name="search_term" value="{html.escape(form['search_term'])}"></label>
<label>From <input type="date" name="from_date" value="{html.escape(form['from_date'])}"></label>
<label>To <input type="date" name="to_date" value="{html.escape(form['to_date'])}"></label>
{tool_controls(tools_for("search"), form)}
<label class="check"><input type="hidden" name="refresh" value="0"><input type="checkbox" name="refresh" value="1"{' checked' if form['refresh'] == '1' else ''}> Fetch afresh from OpenAlex, ignoring the cache</label>
<button type="submit">Search</button>
</form>
<form class="toolform" data-mode="paper" method="get" action="/">
<input type="hidden" name="mode" value="paper">
<label>Find by title <input id="work_title" autocomplete="off"></label>
<div id="work_choices" class="choices" hidden></div>
<label>DOI or OpenAlex work ID <input name="doi" value="{html.escape(form['doi'])}" required></label>
<label>From <input type="date" name="from_date" value="{html.escape(form['from_date'])}"></label>
<label>To <input type="date" name="to_date" value="{html.escape(form['to_date'])}"></label>
{tool_controls(tools_for("paper"), form)}
<label class="check"><input type="hidden" name="refresh" value="0"><input type="checkbox" name="refresh" value="1"{' checked' if form['refresh'] == '1' else ''}> Fetch afresh from OpenAlex, ignoring the cache</label>
<button type="submit">Search</button>
</form>
<form class="toolform" data-mode="author" method="get" action="/">
<input type="hidden" name="mode" value="author">
<label>Find by name <input id="author_name" autocomplete="off"></label>
<div id="author_choices" class="choices" hidden></div>
<label>OpenAlex author ID or ORCID <input name="author" value="{html.escape(form['author'])}" required></label>
<label>From <input type="date" name="from_date" value="{html.escape(form['from_date'])}"></label>
<label>To <input type="date" name="to_date" value="{html.escape(form['to_date'])}"></label>
{tool_controls(tools_for("author"), form)}
<label class="check"><input type="hidden" name="refresh" value="0"><input type="checkbox" name="refresh" value="1"{' checked' if form['refresh'] == '1' else ''}> Fetch afresh from OpenAlex, ignoring the cache</label>
<button type="submit">Search</button>
</form>
<form class="toolform" data-mode="institution" method="get" action="/">
<input type="hidden" name="mode" value="institution">
<label>Find by name <input id="institution_name" autocomplete="off"></label>
<div id="institution_choices" class="choices" hidden></div>
<label>OpenAlex institution ID or ROR ID <input name="institution" value="{html.escape(form['institution'])}" required></label>
<label>Domain <select name="domain" data-level="domain" data-value="{html.escape(form['domain'])}" required></select></label>
<label>Field <select name="field" data-level="field" data-value="{html.escape(form['field'])}" required></select></label>
<label>Subfield <select name="subfield" data-level="subfield" data-value="{html.escape(form['subfield'])}"></select></label>
<label>Topic <select name="topic" data-level="topic" data-value="{html.escape(form['topic'])}"></select></label>
<label>From <input type="date" name="from_date" value="{html.escape(form['from_date'])}"></label>
<label>To <input type="date" name="to_date" value="{html.escape(form['to_date'])}"></label>
{tool_controls(tools_for("institution"), form)}
<label class="check"><input type="hidden" name="refresh" value="0"><input type="checkbox" name="refresh" value="1"{' checked' if form['refresh'] == '1' else ''}> Fetch afresh from OpenAlex, ignoring the cache</label>
<button type="submit">Search</button>
</form>
</aside>
<main>
<div id="progress" class="panel" hidden><span id="stage"></span> <progress id="bar"></progress> <span id="count"></span> <button type="button" id="stop">Stop</button></div>
<div id="results">{result}</div>
</main>
</div>
<script src="/dashboard.js"></script>
</body>
</html>
"""

def report_progress(job, stage, done, total):
    """
    Record the progress of a search. A search that has been stopped ends
    here: SystemExit ends its thread without a traceback.
    """
    if threading.current_thread() is not job["thread"]:
        raise SystemExit
    job.update(stage=stage, done=done, total=total)

def run_job(server, job, form):
    """
    Run a search in the background, keeping its results, or why it failed,
    in its job for /result.
    """
    try:
        #Only one search uses the cache at a time, so a search started meanwhile waits here;
        #a stopped search releases the cache when its thread ends
        with server.cacheLock:
            if threading.current_thread() is not job["thread"]:
                return
            job["stage"] = "starting"
            server.cache.progress = lambda stage, done, total: report_progress(job, stage, done, total)
            server.cache.refresh = form["refresh"] == "1"
            server.cache.refreshed = set()
            try:
                result = run_tool(server.cache, form)
            finally:
                server.cache.refresh = False
                server.cache.progress = None
            if threading.current_thread() is not job["thread"]:
                return
            if server.args.use_cache:
                server.cache.saveCache(server.args.cache_file)
    except Exception as error:
        if threading.current_thread() is not job["thread"]:
            return
        traceback.print_exc()
        result = RENDERERS["error"]({"kind": "error", "text": f"The search failed: {describe_error(error)}"})
    job["result"] = result
    job["running"] = False
    job["finished"] = time.time()

def author_candidates(c, name):
    """
    Return the authors OpenAlex suggests for a name, for the dashboard's find box.
    """
    candidates = []
    for result in c.autocompleteAuthors(name):
        details = f"{result.get('hint') or ''} · {result.get('works_count')} works"
        if result.get("external_id"):
            details = details + " · ORCID " + result["external_id"].rsplit("/", 1)[-1]
        candidates.append({
            "name": result["display_name"],
            "details": details,
            "value": result["id"].rsplit("/", 1)[-1],
        })
    return candidates

def topic_suggestions(c, author, from_date, to_date):
    """
    Return the subfield and field names of an author's works between from_date
    and to_date, most common first, as suggestions for a topic box.
    """
    author, items = author_works(c, author, from_date, to_date)
    counts = {}
    for item in items:
        names = set()
        names.update(topic_names(item, "subfield", 1))
        names.update(topic_names(item, "field", 1))
        for name in names:
            counts[name] = counts.get(name, 0) + 1
    suggestions = []
    for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        suggestions.append(name)
    return suggestions

def work_candidates(c, title):
    """
    Return the works OpenAlex suggests for a title, for the dashboard's find box.
    """
    candidates = []
    for result in c.autocompleteWorks(title):
        if result.get("external_id"):
            value = result["external_id"].replace("https://doi.org/", "")
        else:
            value = result["id"].rsplit("/", 1)[-1]
        candidates.append({
            "name": result["display_name"],
            "details": result.get("hint") or "",
            "value": value,
        })
    return candidates

def institution_candidates(c, name):
    """
    Return the institutions OpenAlex suggests for a name, for the dashboard's find box.
    """
    candidates = []
    for result in c.autocompleteInstitutions(name):
        candidates.append({
            "name": result["display_name"],
            "details": result.get("hint") or "",
            "value": result["id"].rsplit("/", 1)[-1],
        })
    return candidates

def topic_children(c, level, parent):
    """
    Return the domains, or the fields, subfields or topics within `parent`,
    each with its short OpenAlex ID, in order of name, for the dashboard's dropdowns.
    """
    children = []
    for result in c.topicChildren(level, parent):
        children.append({"name": result["display_name"], "value": result["id"].rsplit("/", 1)[-1]})
    children.sort(key=lambda child: child["name"])
    return children

class DashboardHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            url = urlparse(self.path)
            if self.server.token is not None and not self.authorised(url):
                return
            self.route(url)
        except Exception as error:
            traceback.print_exc()
            self.send_content(f"Request failed: {describe_error(error)}", "text/plain", 500)

    def authorised(self, url):
        """
        Return whether a request carries the dashboard's token, in its cookie
        or in its address. A request with the token in its address is given the
        cookie and redirected to the same address without the token, so that
        the token never appears in shared links. A request without the token
        is refused.
        """
        cookieName = f"papervis_token_{self.server.server_port}"
        token = self.server.token.encode()
        cookies = SimpleCookie(self.headers.get("Cookie"))
        if cookieName in cookies and hmac.compare_digest(cookies[cookieName].value.encode(), token):
            return True

        query = parse_qs(url.query)
        if hmac.compare_digest(query.get("token", [""])[-1].encode(), token):
            query.pop("token")
            location = url.path
            if query:
                location = location + "?" + urlencode(query, doseq=True)
            self.send_response(303)
            self.send_header("Set-Cookie", f"{cookieName}={self.server.token}; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False

        self.send_content("This PaperVis dashboard needs a token. Open the address that was printed when the dashboard was started.",
                          "text/plain", 403)
        return False

    def route(self, url):
        """
        Answer a GET request for the given URL.
        """
        if url.path == "/plotly.js":
            self.send_content(self.server.plotlyjs, "application/javascript")
        elif url.path in STATIC_FILES:
            filename, contentType = STATIC_FILES[url.path]
            #The browser must check for a newer copy each time, so that a changed file is always used
            with open(os.path.join(STATIC_DIR, filename)) as file:
                self.send_content(file.read(), contentType, noCache=True)
        elif url.path == "/status":
            job = self.server.jobs[parse_qs(url.query)["job"][0]]
            self.send_content(json.dumps({
                "running": job["running"],
                "stage": job["stage"],
                "done": job["done"],
                "total": job["total"],
            }), "application/json")
        elif url.path == "/result":
            self.send_content(self.server.jobs[parse_qs(url.query)["job"][0]]["result"], "text/html")
        elif url.path == "/search":
            #Each search is a job of its own, so that each window follows and stops only its own search
            form = read_form(url.query)
            jobId = secrets.token_hex(8)
            job = {"running": True, "stage": "waiting", "done": 0, "total": None, "result": "", "thread": None,
                   "finished": None}
            job["thread"] = threading.Thread(target=run_job, args=(self.server, job, form), daemon=True)
            with self.server.jobsLock:
                #Forget searches that ended over an hour ago
                for oldId in list(self.server.jobs):
                    finished = self.server.jobs[oldId]["finished"]
                    if finished is not None and time.time() - finished > 3600:
                        del self.server.jobs[oldId]
                self.server.jobs[jobId] = job
            job["thread"].start()
            self.send_content(json.dumps({"job": jobId}), "application/json")
        elif url.path == "/authors":
            self.send_lookup(author_candidates, parse_qs(url.query)["name"][0])
        elif url.path == "/works":
            self.send_lookup(work_candidates, parse_qs(url.query)["title"][0])
        elif url.path == "/institutions":
            self.send_lookup(institution_candidates, parse_qs(url.query)["name"][0])
        elif url.path == "/children":
            query = parse_qs(url.query)
            self.send_lookup(lambda cache, level: topic_children(cache, level, query.get("parent", [""])[0]),
                             query["level"][0])
        elif url.path == "/topics":
            query = parse_qs(url.query)
            self.send_candidates(lambda cache, author: topic_suggestions(cache, author, query["from_date"][0],
                                                                         query["to_date"][0]),
                                 query["author"][0])
        elif url.path == "/stop":
            job = self.server.jobs[parse_qs(url.query)["job"][0]]
            job.update(running=False, thread=None, finished=time.time())
            self.send_content("{}", "application/json")
        else:
            self.send_content(page(read_form(url.query), ""), "text/html")

    def send_candidates(self, lookup, text):
        """
        Send the candidates for a find box, or why the lookup failed, as JSON.
        """
        #A lookup must not wait for a running search, since that would stall the whole server
        if not self.server.cacheLock.acquire(blocking=False):
            reply = {"candidates": [], "error": "Lookups are not available while a search is running"}
            self.send_content(json.dumps(reply), "application/json")
            return
        #A lookup must not report progress: that belongs to searches, and stops any thread that is not the search's
        progress = self.server.cache.progress
        self.server.cache.progress = None
        try:
            reply = {"candidates": lookup(self.server.cache, text), "error": None}
        except Exception as error:
            traceback.print_exc()
            reply = {"candidates": [], "error": f"Lookup failed: {describe_error(error)}"}
        finally:
            self.server.cache.progress = progress
            self.server.cacheLock.release()
        self.send_content(json.dumps(reply), "application/json")

    def send_lookup(self, lookup, text):
        """
        Send the candidates for a find box or dropdown, or why the lookup
        failed, as JSON, using the lookup cache, so that a running search does
        not hold the lookup up. Lookups take turns with each other.
        """
        with self.server.lookupLock:
            try:
                reply = {"candidates": lookup(self.server.lookupCache, text), "error": None}
                if self.server.args.use_cache:
                    self.server.lookupCache.saveCache(self.server.args.cache_file)
            except Exception as error:
                traceback.print_exc()
                reply = {"candidates": [], "error": f"Lookup failed: {describe_error(error)}"}
        self.send_content(json.dumps(reply), "application/json")

    def log_request(self, code="-", size="-"):
        if self.command != "GET":
            super().log_request(code, size)

    def send_content(self, text, contentType, status=200, noCache=False):
        body = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", contentType + "; charset=utf-8")
        if noCache:
            self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    #Get command line arguments
    # keyword arguments are
    # 1) port - The port to serve the dashboard on. default is 8000
    # 2) use_cache - if set to 1, will use the cache, if set to 0, will not use the cache default 1
    # 3) apikey - The OpenAlex API key. default is no key
    # 4) cache_file - The filename of the cache. default is cache.db
    # 5) token - Require a token to use the dashboard, for shared machines. With no value a token is made up. default is no token

    report_errors_briefly()

    #Parse keyword arguments using argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", dest="port", type=int, default=8000, help="Port to serve the dashboard on. Default is 8000.")
    parser.add_argument("--use_cache", dest="use_cache", type=int, default=1, help="Use cache. 1 to use cache, 0 to not use cache. Default is 1.")
    parser.add_argument("--apikey", dest="apikey", default=None, help="OpenAlex API key. Default is no key.")
    parser.add_argument("--cache_file", dest="cache_file", default="cache.db", help="Filename of the cache. Default is cache.db.")
    parser.add_argument("--token", dest="token", nargs="?", const="", default=None, help="Require a token to use the dashboard, for shared machines. Give a value to choose the token, or none to have one made up. Default is no token.")
    args = parser.parse_args()

    #Serve on the loopback interface only
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    server.args = args
    server.cache = open_cache(args)
    server.cacheLock = threading.Lock()
    #Find boxes and dropdowns look things up through a second connection to the same cache file, so that they need not wait for a search
    server.lookupCache = open_cache(args)
    server.lookupLock = threading.Lock()
    #A token is only needed on a shared machine; --token with no value means make one up
    server.token = args.token
    if server.token == "":
        server.token = secrets.token_urlsafe(16)
    server.plotlyjs = get_plotlyjs()
    server.jobs = {}
    server.jobsLock = threading.Lock()

    if server.token is None:
        print(f"Dashboard at http://127.0.0.1:{args.port}/")
    else:
        print(f"Dashboard at http://127.0.0.1:{args.port}/?token={server.token}")
    server.serve_forever()
