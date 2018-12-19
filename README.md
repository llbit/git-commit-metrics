# Git Commit Metrics

A tool for counting cumulative changes per author for Git repositories.
Can output text, CSV, or LaTeX.

This program sums the output from `git show --numstat` to get actual number of
inserted/removed lines, unlike other line counting tools which use `--stat` to
estimate line counts (good luck with that, lol).

## Basic Usage

1. `python countlines.py <path-to-repo> --by=name --output=tex > stats.tex`
2. `xelatex stats.tex`

## Usage with Alias File

An alias file can be used to map email addresses to names. This is handy when
one or more authors have been inconsistent in their use of the author field in
their commits.

1. Generate an initial alias file:
    `python countlines.py <path-to-repo> --output=alias > aliasfile`
2. Edit `aliasfile`
3. `python countlines.py <path-to-repo> --alias=aliasfile --by=name --output=csv > stats.csv`

## Example Output

Output can be written as a TeX file to produce pretty tables for articles etc.
Here is an example of the TeX output:

![example table](https://raw.githubusercontent.com/llbit/git-commit-metrics/master/example-table.png)


This table was generated with the following commands:

    ./countlines.py https://bitbucket.org/extendj/extendj --alias=aliases --by=name --output=tex --limit=6 > example.tex
    xelatex example.tex
    convert -background White -layers flatten -density 120 -antialias example.pdf example-table.png

