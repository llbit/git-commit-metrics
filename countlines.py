#!/usr/bin/env python3
# Copyright (c) 2018-2025, Jesper Öqvist
import argparse
import sys, os, subprocess, threading
import re
from concurrent.futures import ThreadPoolExecutor

from datetime import datetime

strptime = datetime.strptime
re_auth = re.compile(r'^(.+)#(.*)')
re_edits = re.compile(r'^(\d+)\s+(\d+)') # Binary files start with - -.

class Author:
    def __init__(self, name, email, first_date):
        self.name = name
        self.email = email
        self.first_date = first_date
        self.last_date = first_date
        self.commits = 0
        self.added = 0
        self.deleted = 0

    def edits(s):
        return s.added + s.deleted

    def report(s, keys, totlines):
        row = [""] * len(keys)
        for i,key in enumerate(keys):
            if key == 'name':
                row[i] = s.name
            elif key == 'email':
                row[i] = s.email
            elif key == 'name_email':
                row[i] = f'{s.name} <{s.email}>'
            elif key == 'commits':
                row[i] = s.commits
            elif key == 'added':
                row[i] = s.added
            elif key == 'deleted':
                row[i] = s.deleted
            elif key == 'edits':
                row[i] = s.edits()
            elif key == 'percent':
                row[i] = "%.1f" % ((100.0 * s.edits())/totlines)
            elif key == 'first_date':
                row[i] = s.first_date
            elif key == 'last_date':
                row[i] = s.last_date
        return row

    def __str__(s):
        return '%s <%s>' % (s.name, s.email)

# Lookup author in author dict.
def index(authors, mutex, name, email, date, by):
    if by == 'name':
        key = name
    elif by == 'email':
        key = email
    else:
        key = (name, email)
    with mutex:
        if  key not in authors:
            authors[key] = Author(name, email, date)
        return authors[key]

def gather_data(args, repo, alias):
    os.chdir(repo)

    # Check if branch exists
    out, err = subprocess.Popen(['git', 'branch', '--list'], stdout=subprocess.PIPE).communicate()
    allbranches = [branch.replace("*", "").strip() for branch in out.decode(encoding='UTF-8').splitlines()]

    if args.branch not in allbranches:
        raise Exception(f'Branch {args.branch} does not exist')

    authors = {} # Global author dict
    auth_mutex = threading.Lock() # Mutex for the author dict.

    cmd = ['git', 'rev-list']
    if args.since:
        cmd += [f'--since-as-filter={args.since}']
    if args.until:
        cmd += [f'--until={args.until}']
    if args.max_count:
        cmd += [f'--max-count={args.max_count}']
    cmd += [args.branch]
    revs = subprocess.check_output(cmd).split()
    N = len(revs)
    n = 0
    with ThreadPoolExecutor(max_workers=max(1, os.cpu_count() - 2)) as exe:
        futures = []
        for sha1 in revs:
            futures += [exe.submit(get_commit_stats, sha1, authors, alias, auth_mutex, args.by)]
        try:
            for f in futures:
                n += 1
                sys.stderr.write('\rcommit: %d / %d%s' % (n, N, ' '*15))
                auth, date, added, deleted = f.result()
                auth.commits += 1
                auth.added += added
                auth.deleted += deleted
                if strptime(date, '%Y-%m-%d') < strptime(auth.first_date, '%Y-%m-%d'):
                    auth.first_date = date
                if strptime(date, '%Y-%m-%d') > strptime(auth.last_date, '%Y-%m-%d'):
                    auth.last_date = date
        except KeyboardInterrupt as e:
            exe.shutdown(wait=True, cancel_futures=True)
            raise KeyboardInterrupt()
    sys.stderr.write('\r%s\r' % (' ' * 25))
    return authors

# Get the statistics for a single commit
def get_commit_stats(sha1: str, authors: dict, alias: dict, mutex, by: str):
    with subprocess.Popen(['git', 'show', sha1, '--numstat', '--format=%an#%ae#%ad', '--date=short'], stdout=subprocess.PIPE) as proc:
        out, err = proc.communicate()
        out = out.decode(encoding='UTF-8')
        lines = out.splitlines()
        auth_line = lines[0].split("#")
        auth_line = auth_line[0] + "#" + auth_line[1]
        date = lines[0].split("#")[-1]

        auth_match = re_auth.match(auth_line)
        if not auth_match:
            raise Exception('Malformed author line? [%s]' % auth_line)

        name,email = auth_match.group(1), auth_match.group(2)
        auth = index(authors, mutex, alias.get(email, name), email, date, by)

        added = 0
        deleted = 0
        for ln in lines[1:]:
            edits = re_edits.match(ln)
            if edits:
                added += int(edits.group(1))
                deleted += int(edits.group(2))
        return (auth, date, added, deleted)

COLNAMES={
'name': 'Author',
'email': 'Author',
'name_email': 'Author',
'commits': 'Commits',
'added': 'Inserted',
'deleted': 'Removed',
'edits': 'Total',
'percent': 'Percent',
'first_date': 'First commit',
'last_date': 'Last commit',
}

COLNAMES_TEX={
'name': '\\emph{Author}',
'email': '\\emph{Author',
'name_email': '\\emph{Author}',
'commits': '\\emph{Commits}',
'added': '\\emph{Inserted}',
'deleted': '\\emph{Removed}',
'edits': '$\\Sigma\\,\\downarrow$',
'percent': '\\%',
'first_date': '\\emph{First commit}',
'last_date': '\\emph{Last commit}',
}

def output_data(args, authors):
    totlines = sum(map(lambda x: x.edits(), authors.values()))
    sortkey = lambda a: a.edits() if args.sort == 'edits' else a.commits
    authors = sorted(authors.values(), key=sortkey, reverse=True)
    keys = list(args.columns)
    for i,k in enumerate(keys):
        if k == 'author':
            if args.by == 'both':
                keys[i] = 'name_email'
            else:
                keys[i] = args.by

    if args.limit != None:
        authors = authors[:int(args.limit)]
    if args.output == 'plaintext':
        rows = [[COLNAMES[c] for c in keys]]
        lens = [ len(r) for r in rows[0] ]
        for auth in authors:
            row = auth.report(keys, totlines)
            for i in range(len(lens)):
                lens[i] = max(lens[i], len(str(row[i])))
            rows += [ row ]
        offs = 0
        for row in rows:
            items = []
            for i in range(len(lens)-1):
                items += [ f'{row[i]:<{lens[i]+2}}' ]
            items += [ str(row[-1]) ]
            print(''.join(items))
    elif args.output.startswith('tex'):
        if args.output == 'tex':
            print('''\\documentclass[10pt,border=10pt]{standalone}
\\usepackage{booktabs}
\\usepackage{newtxtext}
\\begin{document}''')
        print('\\begin{tabular}{lrrrrr}')
        print('\\toprule')
        print(' & '.join([COLNAMES_TEX[c] for c in keys]) + '\\\\')
        print('\\midrule')
        for auth in authors:
            print((' & '.join([str(x) for x in auth.report(keys, totlines)]) + ' \\\\'))
        print('\\bottomrule')
        print('\\end{tabular}')
        if args.output == 'tex':
            print('\\end{document}')
    elif args.output == 'csv':
        print(','.join(keys))
        for auth in authors:
            print(','.join([str(x) for x in auth.report(keys, totlines)]))
    elif args.output == 'alias':
        for auth in authors:
            print('%s = %s' % (auth.email, auth.name))


def main():
    parser = argparse.ArgumentParser(description='Counts lines in git project.')
    parser.add_argument('repository', help='The git repository to count lines in.')
    parser.add_argument('--by',
            choices=['name', 'email', 'both'],
            default='both',
            help='Collate by author name, email, or both')
    parser.add_argument('--output',
            choices=['plaintext', 'tex', 'tex-table', 'csv', 'alias'],
            default='plaintext',
            help='Output as TeX document')
    parser.add_argument('--limit',
            help='Maximum number of output rows')
    parser.add_argument('--alias', help='File mapping emails to author names')
    parser.add_argument('--sort',
            choices=['edits', 'commits'],
            default='edits',
            help='Column to sort on')
    parser.add_argument('--since', '--after',
            help='Limit statistics to commits more recent than this date.',
            default=None)
    parser.add_argument('--until', '--before',
            help='Limit statistics to commits older than this date.',
            default=None)
    parser.add_argument('--branch',
            help='Branch to count commits on. Default is "master"',
            default='master')
    parser.add_argument('--max-count', '-n',
            help='Limit to the MAX_COUNT most recent commits.')
    cols = sorted(['author'] + list(COLNAMES.keys()))
    parser.add_argument('--columns',
            default=None,
            help=f'Comma-separated list of column to display. Column names are: {', '.join(cols)}')

    args = parser.parse_args()

    if args.columns is None:
        if args.output == 'csv':
            args.columns = ['author', 'commits', 'added', 'deleted', 'edits', 'percent']
        else:
            args.columns = ['author', 'commits', 'added', 'deleted', 'edits', 'first_date', 'last_date']
    else:
        args.columns = args.columns.split(',')

    for col in args.columns:
        if not col in cols:
            raise Exception(f'ERROR: unknown column name "{col}"')

    repo = args.repository
    if not os.path.isdir(repo):
        # Check out the repo to local directory.
        sys.stderr.write(f'Cloning {repo} into ./repo\n')
        if not os.path.isdir('repo'):
            exit_code = subprocess.call(['git', 'clone', repo, 'repo'])
            if exit_code != 0:
                raise Exception('Failed to fetch git repository %s' % repo)
        repo = 'repo'

    # Read author alias file:
    alias = {}
    if args.alias:
        with open(args.alias, 'r') as fp:
            for ln in fp.readlines():
                email, name = ln.split('=')
                alias[email.strip()] = name.strip()

    try:
        data = gather_data(args, repo, alias)
        output_data(args, data)
    except KeyboardInterrupt as e:
        print("\nKeyboard interrupt. Shutting down...")
        pass

if __name__ == '__main__':
    main()
