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

import math
import textwrap
import matplotlib.pyplot as plt
import plotly.graph_objects as go

def plot_bar_chart(data, output_path, title, xlabel, groups=None):
    """
    Plot counts as a horizontal bar chart with the largest at the top. If
    `groups` gives a group for each bar, bars are coloured by group, with a legend.
    """
    labels = list(data.keys())
    values = list(data.values())

    fig, ax = plt.subplots(figsize=(10, max(4, 0.4 * len(labels))))
    if groups is None:
        ax.barh(labels[::-1], values[::-1])
    else:
        #One coloured series for each group, in order of first appearance, with the bars kept in the order given
        order = []
        for label in labels:
            if groups[label] not in order:
                order.append(groups[label])
        reversedLabels = labels[::-1]
        reversedValues = values[::-1]
        for group in order:
            positions = []
            groupValues = []
            for position, label in enumerate(reversedLabels):
                if groups[label] == group:
                    positions.append(position)
                    groupValues.append(reversedValues[position])
            ax.barh(positions, groupValues, label=group)
        ax.set_yticks(range(len(reversedLabels)))
        ax.set_yticklabels(reversedLabels)
        ax.legend()
    ax.set_xlabel(xlabel)
    ax.set_title(title)

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

def plot_pie(data, output_path, title):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(list(data.values()), labels=list(data.keys()), autopct="%1.1f%%", startangle=140)
    ax.axis("equal")
    ax.set_title(title)

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

def plot_lines(years, series, output_path, title, ylabel):
    fig, ax = plt.subplots(figsize=(12, 7))
    for name, values in series.items():
        ax.plot(years, values, marker="o", label=name)
    ax.set_xlabel("Publication year")
    ax.set_ylabel(ylabel)
    ax.set_xticks(years)
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize="small")
    ax.set_title(title)

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

def plot_columns(counts, output_path, title, ylabel):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(list(counts.keys()), list(counts.values()))
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.xticks(rotation=90)

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")

def plot_country_map(countries, output_path, title):
    names = []
    values = []
    for country in countries.values():
        names.append(country["name"])
        values.append(country["count"])
    figure = go.Figure(
        go.Choropleth(
            locations=names,
            locationmode="country names",
            z=values,
            text=names,
            colorscale="Blues",
            colorbar_title="Works",
        )
    )
    figure.update_geos(showcountries=True, countrycolor="white", coastlinecolor="gray",
                       projection_type="natural earth")
    figure.update_layout(title=title, height=700, margin={"l": 0, "r": 0, "t": 50, "b": 0})

    figure.write_html(output_path, include_plotlyjs=True)

    print(f"Map written to {output_path}")

def plot_map(imap, output_path, title):
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
        hoverText.append(f"<b>{value[1]}</b><br>Number: {value[0]}<br>Click to open OpenAlex URL")
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
    figure.update_layout(title=title, height=700, margin={"l": 0, "r": 0, "t": 50, "b": 0})

    click_script = """
    var plot = document.getElementById('{plot_id}');
    plot.on('plotly_click', function(data) {
        var url = data.points[0].customdata;

        if (url) {
            window.open(url, '_blank', 'noopener,noreferrer');
        }
    });
    """

    figure.write_html(output_path, include_plotlyjs=True, post_script=click_script)

    print(f"Map written to {output_path}")

def plot_network(nodes, links, output_path, title, groupNames=None):
    """
    Draw a network to an image. Nodes are coloured by depth, labelled in the
    legend by `groupNames` if it names that depth, or as "Depth n" otherwise.
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    for (first, second), count in links.items():
        ax.plot([nodes[first]["x"], nodes[second]["x"]], [nodes[first]["y"], nodes[second]["y"]],
                color="gray", linewidth=0.5 + count / 4, zorder=1)
    depths = []
    for node in nodes.values():
        if node["depth"] not in depths:
            depths.append(node["depth"])
    for depth in sorted(depths):
        xs = []
        ys = []
        sizes = []
        for node in nodes.values():
            if node["depth"] == depth:
                xs.append(node["x"])
                ys.append(node["y"])
                sizes.append(30 if node["works"] is None else 30 + 10 * math.sqrt(node["works"]))
        if groupNames and depth in groupNames:
            label = groupNames[depth]
        else:
            label = f"Depth {depth}"
        ax.scatter(xs, ys, s=sizes, label=label, zorder=2)
    for node in nodes.values():
        ax.text(node["x"], node["y"], node["name"], fontsize="x-small", ha="center", va="bottom", zorder=3)
    ax.legend()
    ax.axis("off")
    ax.set_title(textwrap.fill(title, 80))

    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Chart saved to {output_path}")
