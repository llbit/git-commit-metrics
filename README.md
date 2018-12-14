# Git LineCount

A tool for counting cumulative changes per author for Git repositories.
Can output text, CSV, or LaTeX.

This program sums the output from `git show --numstat` to get actual number of
inserted/removed lines, unlike other line counting tools which use `--stat` to
estimate line counts (good luck with that, lol).

Usage:

1. `python countlines.py <path-to-repo> --by=name --output=tex > stats.tex`
2. `xelatex stats.tex`

Usage instructions (with alias file):

1. Generate an initial alias file:
    `python countlines.py <path-to-repo> --output=alias > aliasfile`
2. Edit `aliasfile`
3. `python countlines.py <path-to-repo> --alias=aliasfile --by=name --output=csv > stats.csv`
