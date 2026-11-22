# PaperVis - Visualizing research with OpenAlex

This project is in a very early stage. Options, output, and behavior may change.

The scripts look at OpenAlex works in three ways: the works matching a keyword, the works citing a particular paper, and the works of a particular author, each within a publication-date range. They use a local cache by default.

The purpose of this project is to create simple metrics about research to allow for planning and analysis as well as helping to demonstrate impact of research. The scripts are not intended to be a comprehensive analysis of research, and at present they certainly are not

## Setup

PaperVis needs Python 3. The steps below create a virtual environment in the project directory and install the dependencies into it. They only need to be done once.

On Linux and macOS, in a terminal in the project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, in a Command Prompt or PowerShell window in the project directory:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### OpenAlex API key (strongly recommended)

Using PaperVis with your own OpenAlex API key is strongly recommended. Without a key, every request shares one small free daily allowance with everyone else on your network's IP address, so searches can start failing part way through the day, particularly on a university or company network. A key is free and gives you a much larger daily allowance of your own. Get one at <https://openalex.org/settings/api>, then give it to the dashboard or any tool with `--apikey`:

```sh
python Dashboard.py --apikey YOUR_KEY
```

## Web dashboard

The dashboard is the easiest way to use PaperVis: every tool can be run from it in a web browser, with interactive charts and tables.

To start it, activate the virtual environment and run `Dashboard.py`, adding `--apikey YOUR_KEY` if you have an OpenAlex API key, as is strongly recommended (see above).

On Linux and macOS:

```sh
source .venv/bin/activate
python Dashboard.py
```

On Windows:

```bat
.venv\Scripts\activate
python Dashboard.py
```

Then open `http://127.0.0.1:8000/` in a browser. The dashboard keeps running until you stop it with Ctrl+C in the window where it was started.

The dashboard is served on this machine only (`127.0.0.1`) and is intended for a single user. It accepts these options:

- `--port PORT` sets the port (default `8000`).
- `--use_cache 0` disables loading and saving the cache.
- `--cache_file PATH` selects a cache file.
- `--apikey KEY` supplies an OpenAlex API key, which is strongly recommended. The key can only be set on the command line.
- `--token` requires a token to use the dashboard, for a machine shared with other users, who could otherwise open it too. A token is made up and the address to open is printed when the dashboard starts; `--token VALUE` chooses the token instead, though other users of the machine can then see it in the list of running programs.

### Using the dashboard

The page has four tabs, Keyword, Paper, Author and Institution, matching the four sets of tools described below. Choose a tab and a tool, fill in the search term, paper, author or institution, the dates and any options, and press Search.

- On the Paper, Author and Institution tabs, start typing a title or name in the find box to choose from the matches OpenAlex suggests. This fills in the paper's DOI or the author's or institution's OpenAlex ID.
- On the Institution tab, a domain and a field must be chosen; a subfield and a topic within them can be chosen to narrow the search.
- Where a tool asks for a topic, the box suggests the research fields of the author chosen, but takes any text.
- "Fetch afresh from OpenAlex, ignoring the cache" fetches everything for that search again, replacing what was cached.

A progress bar shows how far the search has got. Stop ends a running search and leaves the form as it was; clicking PaperVis at the top left stops any search and returns to an empty form.

The results are shown as interactive charts and tables. Clicking a column heading sorts a table by that column. "PV Explore" links open a paper or author in the dashboard, ready to search, and clicking an author in a network shows their contact details.

The page address records the search, so a search can be bookmarked, reloaded or shared with someone running their own copy of the dashboard. Adding `&run=0` to an address fills in the form without starting the search. The API key is never part of the address.

Searches can be run from several browser windows at once; they take turns using the cache, and a search waiting for another says so. The find boxes are unavailable while any search is running. If a search fails, the reason is shown on the page and a full description is printed in the window where the dashboard is running.

## Command line tools

Every tool can also be run on its own from the command line, with the virtual environment activated as above. There are four sets of tools: keyword tools, paper tools, author tools and institution tools. Each tool writes its results to files, and tables are written as CSV.

If something goes wrong with a clear cause, such as a paper or author that cannot be found in OpenAlex, a network problem or an unreadable cache file, the tool stops with a one-line message. Anything unexpected is reported with a full Python traceback.

## Keyword tools

Each keyword tool takes the search term as its first argument and looks at the works whose title or abstract matches it.

### Map of institutions

`MapSearch.py` counts institutions represented in the authorships of matching works and writes an interactive HTML map. Click a marker to open its OpenAlex URL.

```sh
python MapSearch.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output map.html
```

### Research field pie chart

`FieldPie.py` counts matching works by their primary topic and writes a pie chart image.

```sh
python FieldPie.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output pie.png
```

### Long tail of research fields

`LongTail.py` lists the less common research fields: those that appear in at least `--min_count` matching works (default `2`) but in less than `--threshold` of them (default `0.02`). For each field it writes the number of works, its share, and up to `--examples` example works (default `3`).

```sh
python LongTail.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --level subfield --output longtail.csv
```

### Field growth

`FieldGrowth.py` plots the number of matching works per publication year for the `--top` most common research fields (default `10`) and writes a line chart image. `--share 1` plots each field's fraction of that year's works instead.

```sh
python FieldGrowth.py "GEANT4" --from 2015-01-01 --to 2024-12-31 --level field --output growth.png
```

### Countries

`CountrySearch.py` counts matching works per country of the authors' institutions. It writes a bar chart image of the `--top` countries (default `20`), a table of all countries (`--table`, default `countries.csv`) and an interactive HTML map (`--map`, default `countries.html`).

```sh
python CountrySearch.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output countries.png
```

### Funders

`FunderSearch.py` counts matching works per funder. It writes a bar chart image of the `--top` funders (default `20`) and a table of all funders (`--table`, default `funders.csv`). Funding information in OpenAlex is incomplete, so the counts are lower bounds.

Each funder's type, such as government or nonprofit, is taken from OpenAlex's record of the same organisation as an institution; funders with no such record are Unclassified. The bar chart is coloured by type, the table includes it, and a pie chart of works per funder type is also written (`--types`, default `funder_types.png`). `AuthorFunders.py` and `InstitutionFunders.py` do the same, writing `author_funder_types.png` and `institution_funder_types.png`.

```sh
python FunderSearch.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output funders.png
```

### Citations

`CitationStats.py` writes a table of the number of matching works and their total, median and mean citation counts for each research field, or for each publication year with `--by year`. Older works have had longer to be cited, so compare fields within a year where possible.

```sh
python CitationStats.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --by year --output citations.csv
```

### Venues

`VenueSearch.py` counts matching works per journal, conference or repository they were published in. It writes a bar chart image of the `--top` venues (default `20`) and a table of all venues with their type (`--table`, default `venues.csv`).

```sh
python VenueSearch.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output venues.png
```

### Topic pairs

`TopicPairs.py` counts pairs of research fields that appear together on the same matching works, using all of each work's topics. It writes a table of the pairs found in at least `--min_count` works (default `2`) and a heatmap image of the `--top` most common fields (`--heatmap`, default `pairs.png`, `--top` default `20`).

```sh
python TopicPairs.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --level subfield --output pairs.csv
```

### Institution types

`InstitutionTypes.py` counts matching works by the types of their authors' institutions, such as Education, Company or Government. A work counts once for each type it involves, and a work with no institution, or an institution with no type, counts as Unclassified. It writes a bar chart image and a table (`--table`, default `institution_types.csv`).

```sh
python InstitutionTypes.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output institution_types.png
```

### Paper list

`PaperList.py` writes a table of all matching works, most cited first, with their date, venue, link and citation count (`--output`, default `papers.csv`). The dashboard shows only the most cited of them, 200 by default.

```sh
python PaperList.py "GEANT4" --from 2024-01-01 --to 2024-12-31
```

### Authors

`KeywordAuthors.py` counts matching works per author. It writes a bar chart image of the `--top` authors (default `20`) and a table of all authors (`--table`, default `keyword_authors.csv`).

```sh
python KeywordAuthors.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output keyword_authors.png
```

### Open access and work types

- `OpenAccess.py` counts matching works by open-access status and writes a pie chart image (`--output`, default `open_access.png`). `--by_year 1` plots the number of works with each status per publication year instead.
- `WorkTypes.py` counts matching works by type, such as article, preprint or review, and writes a pie chart image (`--output`, default `work_types.png`).

### International collaboration

`InternationalCollaboration.py` plots, for each publication year, the percentage of matching works whose authors are in more than one country, and writes a line chart image (`--output`, default `international.png`). Works with no known author country are left out. Works with very long author lists are fetched in full so that no country is missed, which makes the first search slower.

### Team size

`TeamSize.py` counts matching works by their number of authors and writes a chart image (`--output`, default `team_size.png`). `--by_year 1` plots the mean number of authors per work in each publication year instead. As for international collaboration, works with very long author lists are fetched in full.

## Paper tools

Each paper tool takes a paper as its first argument: its DOI, with or without `https://doi.org/`, or its OpenAlex work ID, such as `W2741809807`. For the tools about citing works, `--from` and `--to` select the publication dates of the citing works.

### Citing papers

`CitingPapers.py` lists the works citing the paper, most cited first, with their date, venue, link and citation count (`--output`, default `citing.csv`).

```sh
python CitingPapers.py 10.xxxx/xxxxx --from 2020-01-01 --to 2024-12-31
```

### References

`References.py` lists the works the paper cites, most cited first, with their date, venue, link and citation count (`--output`, default `references.csv`), and reports how many of them were found in OpenAlex. Unlike the other paper tools, it uses all dates unless `--from` or `--to` is given, when they select the publication dates of the references. On the dashboard, untick "All dates" to use the dates on the form.

```sh
python References.py 10.xxxx/xxxxx
```

### Co-cited papers

`CoCited.py` counts the papers cited alongside the paper by the works citing it, and shows the `--top` most often co-cited (default `20`). It writes a bar chart image (`--output`, default `co_cited.png`) and a table (`--table`, default `co_cited.csv`).

```sh
python CoCited.py 10.xxxx/xxxxx --from 2020-01-01 --to 2024-12-31
```

### Authors of a paper

`PaperAuthors.py` prints the paper's authors in order, each with their ORCID (or their OpenAlex author ID if they have no ORCID) and their affiliations, and writes them to a table (`--output`, default `paper_authors.csv`). It does not use `--from` or `--to`.

```sh
python PaperAuthors.py 10.xxxx/xxxxx
```

### Citing fields, authors and venues

- `CitingFields.py` counts the citing works by research field. It accepts `--level`, `--all_topics` and `--top` (default `20`), and writes `citing_fields.png` and `citing_fields.csv` (`--table`).
- `CitingAuthors.py` counts the citing works by author, and writes `citing_authors.png` and `citing_authors.csv`.
- `CitingVenues.py` counts the citing works by venue, and writes `citing_venues.png` and `citing_venues.csv`.

`CitingAuthors.py` and `CitingVenues.py` also accept `--top` (default `20`) for the bar chart.

### Citations over time

`CitationTimeline.py` counts the citing works per publication year, or per month with `--by month`, including periods with none. It writes `citation_timeline.png` and `citation_timeline.csv`.

```sh
python CitationTimeline.py 10.xxxx/xxxxx --from 2015-01-01 --to 2024-12-31 --by year
```

### Long tail of citing fields

`CitingLongTail.py` lists the less common research fields among the citing works, as `LongTail.py` does for a keyword: those with at least `--min_count` citing works (default `1`) but less than `--threshold` of them (default `0.02`), with up to `--examples` example citing works each (default `3`). It writes a table (`--output`, default `citing_longtail.csv`).

### Citing institutions and countries

`CitingInstitutions.py` writes an interactive HTML map of the institutions of the citing works (`--output`, default `citing_institutions.html`) and a table of them (`--table`, default `citing_institutions.csv`).

`CitingCountries.py` writes a map of the countries of the citing works, coloured by the number of citing works (`--output`, default `citing_countries.html`), and a table (`--table`, default `citing_countries.csv`).

`CitingInstitutionTypes.py` counts the citing works by institution type, as `InstitutionTypes.py` does, and writes `citing_institution_types.png` and `citing_institution_types.csv`.

### Self-citations

`SelfCitations.py` reports how many of the citing works share an author with the paper, and writes a table of those works with the shared authors (`--output`, default `self_citations.csv`).

## Author tools

Each author tool takes an author as its first argument: their OpenAlex author ID, such as `A5023888391`, or their ORCID, such as `0000-0002-1825-0097`, each with or without its URL prefix. `--from` and `--to` select the publication dates of the author's works.

### Finding an author

`FindAuthor.py` prints the authors OpenAlex suggests for a name, with their OpenAlex ID, institution, number of works and ORCID. OpenAlex sometimes splits one person into several author records, so the institution and number of works help to pick the right one.

```sh
python FindAuthor.py "yoshua bengio"
```

### Publications

`AuthorPublications.py` lists the author's works, newest first, with their date, venue, link and citation count (`--output`, default `author_publications.csv`). `AuthorOutput.py` counts their works per publication year and writes `author_output.png` and `author_output.csv`.

```sh
python AuthorPublications.py 0000-0002-1825-0097 --from 2015-01-01 --to 2024-12-31
```

### Fields, co-authors and venues

- `AuthorFields.py` counts the author's works by research field. It accepts `--level`, `--all_topics` and `--top` (default `20`), and writes `author_fields.png` and `author_fields.csv`.
- `CoAuthors.py` counts the works the author shares with each co-author, and writes `co_authors.png` and `co_authors.csv`.
- `AuthorVenues.py` counts the author's works by venue, and writes `author_venues.png` and `author_venues.csv`.

`CoAuthors.py` and `AuthorVenues.py` also accept `--top` (default `20`) for the bar chart.

### Co-author institutions and countries

`CoAuthorMap.py` writes an interactive HTML map of the institutions of the author's co-authors (`--output`, default `co_author_map.html`) and a table of them (`--table`, default `co_author_institutions.csv`). `CoAuthorCountries.py` writes a map of the co-authors' countries, coloured by the number of shared works (`--output`, default `co_author_countries.html`), and a table (`--table`, default `co_author_countries.csv`).

### Citations per year

`AuthorCitations.py` charts the citations the author's work received each year, for the years from `--from` to `--to`, and writes `author_citations.png` and `author_citations.csv`. The figures come from the author's OpenAlex record, which only covers recent years.

### Co-author network

`CoAuthorNetwork.py` draws the network of co-authorship around the author: their co-authors, the co-authors of those, and so on for `--depth` steps (`1` to `4`, default `2`). Only co-authors sharing at least `--min_shared` papers (default `4`) are followed and linked, and at most `--max_authors` authors (default `200`) are looked at. It writes an image of the network (`--output`, default `co_author_network.png`), a table of the authors (`--table`, default `co_author_network.csv`) and a table of the links (`--links`, default `co_author_links.csv`).

```sh
python CoAuthorNetwork.py 0000-0002-1825-0097 --from 2015-01-01 --to 2024-12-31 --depth 2
```

### Possible reviewers

`PossibleReviewers.py` suggests possible reviewers for the author's work: people who have published with the author's close co-authors (those sharing at least `--min_shared` papers, default `4`) but have not published with the author themselves in the last `--conflict_years` years (default `5`) or in the dates searched. Candidates are ranked by how many of the author's co-authors connect them to the author, then by their papers with those co-authors. The top `--candidates` (default `50`) are checked, and those who first published less than `--min_career_years` years ago (default `5`), or have published nothing this year or in the previous `--active_years` years (default `1`), are left out. `--topic TEXT` counts only papers whose topic, subfield or field name contains the text. It writes an image of the network (`--output`, default `possible_reviewers.png`) and a table (`--table`, default `possible_reviewers.csv`) including each candidate's topic overlap with the author and their first and last years of publication.

### Contact details

`AuthorContact.py` gathers what OpenAlex holds that helps to contact the author: their ORCID, their last known institutions with home pages, their full affiliations as given on their papers, and their most recent papers as a corresponding author (up to `--papers`, default `10`), whose publisher pages usually give an email address. OpenAlex holds no email addresses itself. It prints the details and writes the papers to a table (`--output`, default `author_contact.csv`).

### Summary

`AuthorSummary.py` reports the number of the author's works in the dates searched, their total and mean citations, and the h-index and i10-index of those works, alongside OpenAlex's figures for the author's whole career. It prints them and writes them to a table (`--output`, default `author_summary.csv`).

### Top papers

`AuthorTopPapers.py` lists the author's works, most cited first, with their date, venue, link and citation count (`--output`, default `author_top_papers.csv`). The dashboard shows only the most cited of them, 200 by default.

### Who cites them and who they cite

- `WhoCitesThem.py` counts, for each author, the works citing any of the author's works from the dates searched. The citing works may be of any date.
- `WhoTheyCite.py` counts, for each author, how many of the author's works from the dates searched cite them.

Both leave out the author's citations of their own work unless `--include_self 1` is given, accept `--top` (default `20`) for the bar chart, and write a bar chart image and a table (`who_cites_them.png` and `who_cites_them.csv`, or `who_they_cite.png` and `who_they_cite.csv`). Both can take a long time for a prolific author.

### Affiliation history

`AffiliationHistory.py` lists the institutions OpenAlex records for the author in the years from `--from` to `--to`, with the years of each, most recent first (`--output`, default `affiliation_history.csv`).

### Funders

`AuthorFunders.py` counts the author's works per funder. It writes a bar chart image of the `--top` funders (default `20`) and a table of all funders (`--table`, default `author_funders.csv`). As for `FunderSearch.py`, the counts are lower bounds.

## Institution tools

Each institution tool takes an institution as its first argument: its OpenAlex institution ID, such as `I39555362`, or its ROR ID. Exactly one of `--field`, `--subfield` or `--topic` must also be given, with the OpenAlex ID of the field, subfield or topic, such as `--field 17` for Computer Science. A work belongs to the institution when the institution is among its corresponding authors' institutions, and to the field, subfield or topic when any of its topics falls within it. `--from` and `--to` select the publication dates of the works.

### Works

`InstitutionWorks.py` lists the works, most cited first, with their date, venue, link, citation count and corresponding author at the institution where OpenAlex marks one (`--output`, default `institution_works.csv`). The dashboard shows only the most cited of them, 200 by default.

```sh
python InstitutionWorks.py I39555362 --field 17 --from 2024-01-01 --to 2024-12-31
```

### Funders and journals

- `InstitutionFunders.py` counts the works per funder, and writes a bar chart image of the `--top` funders (default `20`) and a table (`--table`, default `institution_funders.csv`). As for `FunderSearch.py`, the counts are lower bounds.
- `InstitutionVenues.py` counts the works per journal, conference or repository, and writes a bar chart image of the `--top` venues (default `20`) and a table with their type (`--table`, default `institution_venues.csv`).

### Partner institutions and countries

`InstitutionPartners.py` writes an interactive HTML map of the other institutions of the works' authors (`--output`, default `institution_partners.html`) and a table of them (`--table`, default `institution_partners.csv`). `InstitutionCountries.py` writes a map of the countries of the authors at other institutions, coloured by the number of shared works (`--output`, default `institution_countries.html`), and a table (`--table`, default `institution_countries.csv`). Works with very long author lists are fetched in full so that no partner is missed.

### Partner network

`InstitutionNetwork.py` draws the network of the institution's partners: the `--max_institutions` institutions sharing the most works with it (default `50`), linked to the institution by their shared works and to each other by the works on which they appear together. Partners and links with fewer than `--min_shared` shared works (default `2`) are left out, and so are works with more than `--max_authors` authors (default `10`, at most `99`), as large collaborations would link almost every partner to every other. It writes an image of the network (`--output`, default `institution_network.png`), a table of the institutions (`--table`, default `institution_network.csv`) and a table of the links (`--links`, default `institution_links.csv`).

### Collaborators and local authors

- `InstitutionCollaborators.py` lists the people outside the institution who appear on at least `--min_works` of its works (default `2`).
- `InstitutionAuthors.py` lists the people at the institution who appear on at least `--min_works` of its works.

For each person they give the number of works and the institutions listed on them. As for the partner network, works with more than `--max_authors` authors (default `10`, at most `99`) are left out. Each writes a bar chart image of the `--top` people (default `20`) and a table (`institution_collaborators.png` and `institution_collaborators.csv`, or `institution_authors.png` and `institution_authors.csv`).

## Options

All tools apart from `FindAuthor.py` accept `--from` and `--to` publication dates in `YYYY-MM-DD` format. By default, the date range is approximately the previous year, caching is enabled, and the cache file is `cache.json.gz`.

- `--use_cache 0` disables loading and saving the cache.
- `--cache_file PATH` selects a cache file.
- `--apikey KEY` supplies an OpenAlex API key, which is strongly recommended (see Setup).
- `--output PATH` sets the output filename.
- `--refresh 1` fetches everything afresh from OpenAlex, replacing what is in the cache.

`FieldPie.py` also accepts `--threshold FRACTION` to group smaller topics as "Other" (default `0.02`), and `--show_other 0` to omit that category from the chart.

The tools that group works by research field (`LongTail.py`, `FieldGrowth.py`, `CitationStats.py`, `TopicPairs.py`, `CitingFields.py`, `CitingLongTail.py` and `AuthorFields.py`) accept `--level` to choose how broadly fields are grouped: `topic` (the default), `subfield`, `field` or `domain`. Except for `TopicPairs.py`, they also accept `--all_topics 1` to count all of a work's topics rather than only its primary topic.

## The Cache

This project uses a local cache to avoid repeated queries to the OpenAlex API. Only the parts of a date range that are missing from the cache, or have expired, are fetched; results more than about 100 days old are kept for a month, more recent ones for an hour.

Because of this, the time a search takes is unpredictable. The same search can finish almost at once when everything it needs is cached, and take minutes when it has to be fetched from OpenAlex, depending on what earlier searches have already fetched and how long ago. The cache is stored in a JSON file, which is compressed with gzip. By default, the cache file is named `cache.json.gz`, but you can specify a different filename with the `--cache_file` option. This cache should work as expected, but at present it shouldn't be considered production-ready. If you encounter any issues, please report them.