# Copyright (c) 2018, Jesper Öqvist
import argparse
import ConfigParser
import sys, os, subprocess
import re

class Author:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.commits = 0
        self.added = 0
        self.deleted = 0

    def __str__(s):
        return '%s & %d & %d & %d' % (s.name, s.commits, s.added, s.deleted)

def index(authors, name, email, by_name):
    if by_name:
        key = name
    else:
        key = (name, email)
    if not key in authors:
        authors[key] = Author(name, email)
    return authors[key]

def main():
    authors = {}
    parser = argparse.ArgumentParser(description='Counts lines in git project.')
    parser.add_argument('repository', help='The git repository to count lines in.')
    parser.add_argument('--by-name', dest='by_name', action='store_true',
            help='Collate by author name (ignoring email)')
    parser.add_argument('--alias', help='Author name alias file')
    args = parser.parse_args()
    repo = args.repository
    if not os.path.isdir(repo):
        # Check out the repo to local directory.
        print 'Cloning %s into ./repo' % repo
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
                pseudonym, name = ln.split('=')
                alias[pseudonym.strip()] = name.strip()

    # Process commits.
    os.chdir(repo)
    revs = subprocess.check_output(['git', 'rev-list', 'master']).split()
    re_auth = re.compile('^(.+)#(.*)')
    re_edits = re.compile('^(\d+)\s+(\d+)') # Binary files start with - -.
    n = 0
    for rev in revs:
        n += 1
        sys.stderr.write('\rcommit: %d%s' % (n, ' '*30))
        out,err = subprocess.Popen(['git', 'show', rev, '--numstat', '--format=%an#%ae'], stdout=subprocess.PIPE).communicate()
        lines = out.splitlines()
        auth_line = lines[0]
        auth = re_auth.match(auth_line)
        if not auth:
            raise Exception('Malformed author line? [%s]' % auth_line)
        name,email = auth.group(1), auth.group(2)
        auth = index(authors, alias.get(name, name), email, args.by_name)
        auth.commits += 1
        for ln in lines[1:]:
            edits = re_edits.match(ln)
            if edits:
                auth.added += int(edits.group(1))
                auth.deleted += int(edits.group(2))
    sys.stderr.write('\rdone%s\n' % (' ' * 30))
    authors = sorted(authors.values(), key=lambda x: x.added + x.deleted, reverse=True)
    for auth in authors:
        print auth

if __name__ == '__main__':
    main()
