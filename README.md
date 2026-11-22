# OpenAlex Search Tools

This project is in a very early stage. Options, output, and behavior may change.

The scripts search OpenAlex works for a term within a publication-date range. They use a local cache by default.

The purpose of this project is to create simple metrics about research to allow for planning and analysis as well as helping to demonstrate impact of research. The scripts are not intended to be a comprehensive analysis of research, and at present they certainly are not

## Setup

Install the dependencies:

```sh
pip install -r requirements.txt
```

## Map of institutions

`MapSearch.py` counts institutions represented in the authorships of matching works and writes an interactive HTML map. Click a marker to open its OpenAlex URL.

```sh
python MapSearch.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output map.html
```

## Research field pie chart

`FieldPie.py` counts matching works by their primary topic and writes a pie chart image.

```sh
python FieldPie.py "GEANT4" --from 2024-01-01 --to 2024-12-31 --output pie.png
```

## Options

Both scripts accept `--from` and `--to` publication dates in `YYYY-MM-DD` format. By default, the date range is approximately the previous year, caching is enabled, and the cache file is `cache.json.gz`.

- `--use_cache 0` disables loading and saving the cache.
- `--cache_file PATH` selects a cache file.
- `--apikey KEY` supplies an OpenAlex API key.
- `--output PATH` sets the output filename.

`FieldPie.py` also accepts `--threshold FRACTION` to group smaller topics as "Other" (default `0.02`), and `--show_other 0` to omit that category from the chart.

## The Cache

This project uses a local cache to avoid repeated queries to the OpenAlex API. The cache is stored in a JSON file, which is compressed with gzip. By default, the cache file is named `cache.json.gz`, but you can specify a different filename with the `--cache_file` option. This cache should work as expected, but at present it shouldn't be considered production-ready. If you encounter any issues, please report them.