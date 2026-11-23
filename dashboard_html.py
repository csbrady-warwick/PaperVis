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

import html
import math
import textwrap
from urllib.parse import urlencode
import plotly.graph_objects as go

#What a link to the dashboard's own Paper or Author tab shows, in place of the identifier it uses
EXPLORE = "<span class=\"pv-badge\">PV</span> Explore"

def paper_identifier(value):
    """
    Return the DOI or OpenAlex work ID in a work's link, without its URL prefix.
    """
    if value.startswith("https://doi.org/"):
        return value[len("https://doi.org/"):]
    return value.rsplit("/", 1)[-1]

def wrap_title(text):
    """
    Return a chart title broken into lines of about 80 characters, which
    Plotly does not do itself, and the extra top margin the added lines need.
    """
    lines = textwrap.wrap(text, 80)
    return "<br>".join(lines), 22 * (len(lines) - 1)

def chart(figure, post_script=None, config=None):
    return figure.to_html(full_html=False, include_plotlyjs=False, post_script=post_script, config=config)

def table(header, rows, types=None):
    """
    Return a table as HTML. `types` gives the type of each column: "asLink" for
    a column of web addresses, which are shown as links; "asPaper" for a
    column of DOIs or work IDs, and "asUser" for a column of author IDs or
    ORCIDs, which are shown as a "PV Explore" link to the dashboard's Paper or
    Author tab filled in with that paper or author, ready to search; or None. A cell given as a dict
    with "text" and "link" is shown as a link to that address, whatever its
    column's type, for columns whose rows need different addresses.
    """
    head = ""
    for cell in header:
        head = head + f"<th>{html.escape(str(cell))}</th>"
    body = ""
    for row in rows:
        body = body + "<tr>"
        for position, cell in enumerate(row):
            if isinstance(cell, dict):
                body = body + (f"<td><a href=\"{html.escape(cell['link'])}\" target=\"_blank\" rel=\"noopener noreferrer\">"
                               f"{html.escape(str(cell['text']))}</a></td>")
                continue
            text = html.escape(str(cell))
            if types and types[position] == "asLink" and str(cell).startswith(("http://", "https://")):
                text = f"<a href=\"{text}\" target=\"_blank\" rel=\"noopener noreferrer\">{text}</a>"
            elif types and types[position] == "asPaper" and str(cell):
                address = "/?" + urlencode({"mode": "paper", "doi": paper_identifier(str(cell)), "run": "0"})
                text = f"<a class=\"explore\" href=\"{html.escape(address)}\" target=\"_blank\">{EXPLORE}</a>"
            elif types and types[position] == "asUser" and str(cell):
                address = "/?" + urlencode({"mode": "author", "author": str(cell).rsplit("/", 1)[-1], "run": "0"})
                text = f"<a class=\"explore\" href=\"{html.escape(address)}\" target=\"_blank\">{EXPLORE}</a>"
            body = body + f"<td>{text}</td>"
        body = body + "</tr>"
    return f"<div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"

def bar(counts, title, groups=None):
    """
    Return a horizontal bar chart of counts as HTML, largest at the top. If
    `groups` gives a group for each bar, bars are coloured by group, with a legend.
    """
    labels = list(counts.keys())
    values = list(counts.values())
    if groups is None:
        figure = go.Figure(go.Bar(x=values[::-1], y=labels[::-1], orientation="h"))
    else:
        #One coloured series for each group, in order of first appearance, with the bars kept in the order given
        order = []
        for label in labels:
            if groups[label] not in order:
                order.append(groups[label])
        figure = go.Figure()
        for group in order:
            groupLabels = []
            groupValues = []
            for label, value in zip(labels[::-1], values[::-1]):
                if groups[label] == group:
                    groupLabels.append(label)
                    groupValues.append(value)
            figure.add_trace(go.Bar(x=groupValues, y=groupLabels, orientation="h", name=group))
        figure.update_layout(barmode="stack")
        figure.update_yaxes(categoryorder="array", categoryarray=labels[::-1])
    #Plotly leaves out labels on a crowded axis, so every bar's label is given explicitly
    figure.update_yaxes(tickmode="array", tickvals=labels, ticktext=labels, automargin=True)
    title, extra = wrap_title(title)
    figure.update_layout(title=title, height=max(400, 30 * len(labels)), xaxis_title="Number of works",
                         margin={"t": 100 + extra})
    return chart(figure)

def institution_map(imap, title):
    """
    Return a map of institutions, each marked with its number of works, as HTML.
    """
    longitudes = []
    latitudes = []
    labels = []
    urls = []
    hoverText = []
    for id, value in imap.items():
        if not value[2]:
            continue
        longitudes.append(float(value[2]["longitude"]))
        latitudes.append(float(value[2]["latitude"]))
        labels.append(str(value[0]))
        urls.append(id)
        hoverText.append(f"<b>{html.escape(value[1])}</b><br>Number: {value[0]}<br>Click to open OpenAlex URL")
    figure = go.Figure(
        go.Scattergeo(
            lon=longitudes,
            lat=latitudes,
            text=labels,
            customdata=urls,
            hovertext=hoverText,
            hoverinfo="text",
            mode="markers+text",
            textposition="middle center",
            marker={"size": 24, "color": "white", "line": {"color": "black", "width": 1}},
        )
    )
    figure.update_geos(showland=True, landcolor="lightgray", showocean=True, oceancolor="lightblue",
                       showcountries=True, countrycolor="white", coastlinecolor="gray",
                       projection_type="natural earth")
    title, extra = wrap_title(title)
    figure.update_layout(title=title, height=700, margin={"l": 0, "r": 0, "t": 50 + extra, "b": 0})
    click_script = """
    var plot = document.getElementById('{plot_id}');
    plot.on('plotly_click', function(data) {
        var url = data.points[0].customdata;
        if (url) {
            window.open(url, '_blank', 'noopener,noreferrer');
        }
    });
    """
    return chart(figure, click_script)

#Renderers turn a tool's description of one result, its view, into HTML. There is one for each kind of view.

def render_pie(view):
    figure = go.Figure(go.Pie(labels=list(view["data"].keys()), values=list(view["data"].values())))
    title, extra = wrap_title(view["title"])
    figure.update_layout(title=title, height=700, margin={"t": 100 + extra})
    return chart(figure)

def render_bar(view):
    return bar(view["data"], view["title"], view.get("groups"))

def render_columns(view):
    figure = go.Figure(go.Bar(x=list(view["data"].keys()), y=list(view["data"].values())))
    title, extra = wrap_title(view["title"])
    figure.update_layout(title=title, height=500, yaxis_title=view["ylabel"], margin={"t": 100 + extra})
    figure.update_xaxes(type="category")
    return chart(figure)

def render_line(view):
    figure = go.Figure()
    for name, values in view["series"].items():
        figure.add_trace(go.Scatter(x=view["x"], y=values, mode="lines+markers", name=name))
    title, extra = wrap_title(view["title"])
    figure.update_layout(title=title, height=700, xaxis_title=view["xlabel"], yaxis_title=view["ylabel"],
                         margin={"t": 100 + extra})
    return chart(figure)

def render_heatmap(view):
    figure = go.Figure(go.Heatmap(z=view["matrix"], x=view["labels"], y=view["labels"], colorscale="Viridis",
                                  colorbar_title=view["colorbar"]))
    title, extra = wrap_title(view["title"])
    figure.update_layout(title=title, height=800, margin={"t": 100 + extra})
    return chart(figure)

def render_institution_map(view):
    return institution_map(view["data"], view["title"])

def render_choropleth(view):
    figure = go.Figure(
        go.Choropleth(
            locations=view["locations"],
            locationmode="country names",
            z=view["values"],
            text=view["locations"],
            colorscale="Blues",
            colorbar_title="Works",
        )
    )
    figure.update_geos(showcountries=True, countrycolor="white", coastlinecolor="gray",
                       projection_type="natural earth")
    title, extra = wrap_title(view["title"])
    figure.update_layout(title=title, height=700, margin={"l": 0, "r": 0, "t": 50 + extra, "b": 0})
    return chart(figure)

def render_network(view):
    #Links are drawn first, thicker for more shared papers, so the authors sit on top of them.
    #A view can name the depths in the legend; otherwise they are shown as "Depth n"
    groupNames = view.get("groupNames", {})
    figure = go.Figure()
    for (first, second), count in view["links"].items():
        figure.add_trace(go.Scatter(x=[view["nodes"][first]["x"], view["nodes"][second]["x"]],
                                    y=[view["nodes"][first]["y"], view["nodes"][second]["y"]],
                                    mode="lines", line={"color": "#9fb3c8", "width": 0.5 + count / 4},
                                    hoverinfo="none", showlegend=False))
    depths = []
    for node in view["nodes"].values():
        if node["depth"] not in depths:
            depths.append(node["depth"])
    for depth in sorted(depths):
        xs = []
        ys = []
        sizes = []
        names = []
        hoverText = []
        addresses = []
        for id, node in view["nodes"].items():
            if node["depth"] != depth:
                continue
            xs.append(node["x"])
            ys.append(node["y"])
            sizes.append(10 if node["works"] is None else 10 + 2 * math.sqrt(node["works"]))
            names.append(node["name"])
            #Clicking an institution fills in the Institution tab with it, for the same area and dates, without searching
            if view.get("nodeKind") == "institution":
                query = view["query"]
                hoverText.append(f"<b>{html.escape(node['name'])}</b><br>Works: {node['works']}<br>Click to open this institution")
                addresses.append("/?" + urlencode({"mode": "institution", "institution": id.rsplit("/", 1)[-1],
                                                   "domain": query["domain"], "field": query["field"],
                                                   "subfield": query["subfield"], "topic": query["topic"],
                                                   "from_date": query["from_date"], "to_date": query["to_date"],
                                                   "run": "0"}))
                continue
            #A view can give a node its own hover text and link, None for no link
            if "link" in node:
                hoverText.append(f"<b>{html.escape(node['name'])}</b><br>{html.escape(node['hover'])}")
                addresses.append(node["link"])
                continue
            works = "not fetched" if node["works"] is None else node["works"]
            hoverText.append(f"<b>{html.escape(node['name'])}</b><br>Depth: {depth}<br>Works: {works}<br>Click for their contact details")
            #Clicking an author shows their contact details, for the same dates
            addresses.append("/?" + urlencode({"mode": "author", "tool": "author_contact",
                                               "author": id.rsplit("/", 1)[-1],
                                               "from_date": view["query"]["from_date"],
                                               "to_date": view["query"]["to_date"]}))
        figure.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=names, textposition="top center",
                                    textfont={"size": 9}, marker={"size": sizes}, customdata=addresses,
                                    hovertext=hoverText, hoverinfo="text", name=groupNames.get(depth, f"Depth {depth}")))
    title, extra = wrap_title(view["title"])
    #Dragging pans the network and the mouse wheel zooms it, as on a map
    figure.update_layout(title=title, height=800, margin={"t": 100 + extra},
                         xaxis={"visible": False}, yaxis={"visible": False}, dragmode="pan")
    click_script = """
    var plot = document.getElementById('{plot_id}');
    plot.on('plotly_click', function(data) {
        var url = data.points[0].customdata;
        if (url) {
            window.open(url, '_blank');
        }
    });
    """
    return chart(figure, click_script, {"scrollZoom": True})

def render_table(view):
    return table(view["header"], view["rows"], view.get("types"))

def render_text(view):
    return f"<div>{html.escape(view['text'])}</div>"

def render_error(view):
    return f"<div class=\"error\">{html.escape(view['text'])}</div>"

RENDERERS = {
    "pie": render_pie,
    "bar": render_bar,
    "columns": render_columns,
    "line": render_line,
    "heatmap": render_heatmap,
    "institution_map": render_institution_map,
    "choropleth": render_choropleth,
    "network": render_network,
    "table": render_table,
    "text": render_text,
    "error": render_error,
}
