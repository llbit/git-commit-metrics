#!/usr/bin/env python3
# Copyright (c) 2018, Jesper Öqvist
import argparse
import sys, os, subprocess
import re

class Author:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.commits = 0
        self.added = 0
        self.deleted = 0

    def report(s, by, sep, suffix=''):
        metrics = list(map(lambda x: format(x, ','),
                [s.commits, s.added, s.deleted, s.added + s.deleted]))
        if by == 'name':
            return sep.join([s.name] + metrics) + suffix
        elif by == 'email':
            return sep.join([s.email] + metrics) + suffix
        else:
            return sep.join(["%s <%s>" % (s.name, s.email)] + metrics) + suffix

    def __str__(s):
        return '%s <%s>' % (s.name, s.email)

def index(authors, name, email, by):
    if by == 'name':
        key = name
    elif by == 'email':
        key = email
    else:
        key = (name, email)
    if not key in authors:
        authors[key] = Author(name, email)
    return authors[key]

def main():
    authors = {}
    parser = argparse.ArgumentParser(description='Counts lines in git project.')
    parser.add_argument('repository', help='The git repository to count lines in.')
    parser.add_argument('--by',
            choices=['name', 'email', 'both'],
            default='both',
            help='Collate by author name, email, or both')
    parser.add_argument('--output', dest='output',
            choices=['plaintext', 'tex', 'tex-table', 'csv', 'alias'],
            default='plaintext',
            help='Output as TeX document')
    parser.add_argument('--alias', help='File mapping emails to author names')
    args = parser.parse_args()
    repo = args.repository
    if not os.path.isdir(repo):
        # Check out the repo to local directory.
        sys.stderr.write('Cloning %s into ./repo\n' % repo)
        if not os.path.isdir('repo'):
            exit_code = subprocess.call(['git', 'clone', repo, 'repo'])
            if exit_code != 0:
                raise Exception('Failed to fetch git repository %s' % repo)
        repo = 'repo'

    # Read alias file.
    alias = {}
    if args.alias:
        with open(args.alias, 'r') as fp:
            for ln in fp.readlines():
                email, name = ln.split('=')
                alias[email.strip()] = name.strip()

    # Process commits.
    os.chdir(repo)
    revs = subprocess.check_output(['git', 'rev-list', 'master']).split()
    re_auth = re.compile('^(.+)#(.*)')
    re_edits = re.compile('^(\d+)\s+(\d+)') # Binary files start with - -.
    N = len(revs)
    n = 0
    for rev in revs:
        n += 1
        sys.stderr.write('\rcommit: %d / %d%s' % (n, N, ' '*15))
        out,err = subprocess.Popen(['git', 'show', rev, '--numstat', '--format=%an#%ae'], stdout=subprocess.PIPE).communicate()
        out = out.decode(encoding='UTF-8')
        lines = out.splitlines()
        auth_line = lines[0]
        auth = re_auth.match(auth_line)
        if not auth:
            raise Exception('Malformed author line? [%s]' % auth_line)
        name,email = auth.group(1), auth.group(2)
        auth = index(authors, alias.get(email, name), email, args.by)
        auth.commits += 1
        for ln in lines[1:]:
            edits = re_edits.match(ln)
            if edits:
                auth.added += int(edits.group(1))
                auth.deleted += int(edits.group(2))
    sys.stderr.write('\r%s\r' % (' ' * 25))
    authors = sorted(authors.values(), key=lambda x: x.added + x.deleted, reverse=True)
    if args.output == 'plaintext':
        print('Author Commits Inserted Removed Total')
        for auth in authors:
            print(auth.report(args.by, sep=' '))
    elif args.output.startswith('tex'):
        if args.output == 'tex':
            print('''\documentclass[10pt,border=10pt]{standalone}
\\usepackage{booktabs}
\\usepackage{newtxtext}
\\begin{document}''')
        print('''\\begin{tabular}{lrrrr}
\\toprule
\\emph{Author} & \\emph{Commits} & \\emph{Inserted} & \\emph{Removed} & $\Sigma\,\downarrow$ \\\\
\\midrule''')
        for auth in authors:
            print(auth.report(args.by, sep=' & ', suffix = ' \\\\'))
        print('''\\bottomrule
\\end{tabular}''')
        if args.output == 'tex':
            print('\\end{document}')
    elif args.output == 'csv':
        for auth in authors:
            print(auth.report(args.by, sep=','))
    elif args.output == 'alias':
        for auth in authors:
            print('%s = %s' % (auth.email, auth.name))

if __name__ == '__main__':
    main()
