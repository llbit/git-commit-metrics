#!/usr/bin/env python3
# Copyright (c) 2018-2022, Jesper Öqvist
import argparse
import sys, os, subprocess
import re
import datetime
class Author:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.commits = 0
        self.added = 0
        self.deleted = 0

    def edits(s):
        return s.added + s.deleted

    def report(s, by, totlines):
        metrics = list(map(lambda x: format(x, ','),
                [s.commits, s.added, s.deleted, s.edits()]))
        metrics += ["%.1f" % ((100.0 * s.edits())/totlines)]
        if by == 'name':
            return [s.name] + metrics
        elif by == 'email':
            return [s.email] + metrics
        else:
            return ["%s <%s>" % (s.name, s.email)] + metrics

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
    parser.add_argument('--date',
            help='Date to filter on. Accepts a single date in YYYY-MM-DD format, a closed range in [YYYY-MM-DD;YYYY-MM-DD] format, or an open-ended range in [YYYY-MM-DD;YYYY-MM-DD[ format. Use "now" for today.',
            default=None
            )
    parser.add_argument('--branch',
            help='Branch to count commits on. Default is "master"',
            default='master')

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
    if args.date:
        print(args.date)
        if args.date == 'now':
            args.date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        date_range_pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2});(\d{4}-\d{2}-\d{2})(\]|\[)')
        match = date_range_pattern.match(args.date)
        if match:
            start_date = datetime.datetime.strptime(match.group(1), '%Y-%m-%d')
            end_date = datetime.datetime.strptime(match.group(2), '%Y-%m-%d')

            if match.group(3) == '[':
                end_date = end_date + datetime.timedelta(days=-1)

            if start_date > end_date:
                raise Exception('Start date must be before end date')
            args.date = (start_date, end_date)
        else:
            args.date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
    
   
    
        
    

    # Process commits.
    os.chdir(repo)
    #check if branch exists
    out, err = subprocess.Popen(['git', 'branch', '--list'], stdout=subprocess.PIPE).communicate()

    print(out.decode(encoding='UTF-8').splitlines())
    if args.branch not in [branch.replace("*", "").strip() for branch in out.decode(encoding='UTF-8').splitlines()]:
        raise Exception('Branch %s does not exist' % args.branch)


    revs = subprocess.check_output(['git', 'rev-list', args.branch]).split()
    re_auth = re.compile('^(.+)#(.*)')
    re_edits = re.compile('^(\d+)\s+(\d+)') # Binary files start with - -.
    N = len(revs)
    n = 0
    for rev in revs:
        n += 1
        sys.stderr.write('\rcommit: %d / %d%s' % (n, N, ' '*15))
        out, err = subprocess.Popen(['git', 'show', rev, '--numstat', '--format=%an#%ae#%ad', '--date=short'], stdout=subprocess.PIPE).communicate()
        out = out.decode(encoding='UTF-8')
        lines = out.splitlines()
        auth_line = lines[0]
        date = lines[0].split("#")[-1]
        
        if args.date:
            if isinstance(args.date, tuple):
                if datetime.datetime.strptime(date, '%Y-%m-%d') < args.date[0] or datetime.datetime.strptime(date, '%Y-%m-%d') > args.date[1]:
                    continue
            else:
                if datetime.datetime.strptime(date, '%Y-%m-%d') != args.date:
                    continue

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
    totlines = sum(map(lambda x: x.edits(), authors.values()))
    sortkey = lambda a: a.edits() if args.sort == 'edits' else a.commits
    authors = sorted(authors.values(), key=sortkey, reverse=True)
    if args.limit != None:
        authors = authors[:int(args.limit)]
    if args.output == 'plaintext':
        rows = [['Author','Commits','Inserted','Removed','Total','Percent']]
        lens = [ len(r) for r in rows[0] ]
        for auth in authors:
            row = auth.report(args.by, totlines)
            for i in range(len(lens)):
                lens[i] = max(lens[i], len(row[i]))
            rows += [ row ]
        offs = 0
        for row in rows:
            items = []
            for i in range(len(lens)-1):
                items += f'{row[i]:<{lens[i]+2}}'
            items += row[-1]
            print(''.join(items))
    elif args.output.startswith('tex'):
        if args.output == 'tex':
            print('''\\documentclass[10pt,border=10pt]{standalone}
\\usepackage{booktabs}
\\usepackage{newtxtext}
\\begin{document}''')
        print('''\\begin{tabular}{lrrrrr}
\\toprule
\\emph{Author} & \\emph{Commits} & \\emph{Inserted} & \\emph{Removed} & $\\Sigma\,\\downarrow$ & \\% \\\\
\\midrule''')
        for auth in authors:
            print((' & '.join(auth.report(args.by, totlines)) + ' \\\\'))
        print('''\\bottomrule
\\end{tabular}''')
        if args.output == 'tex':
            print('\\end{document}')
    elif args.output == 'csv':
        for auth in authors:
            print(','.join(auth.report(args.by, totlines)))
    elif args.output == 'alias':
        for auth in authors:
            print('%s = %s' % (auth.email, auth.name))

if __name__ == '__main__':
    main()#!/usr/bin/env python3
# Copyright (c) 2018-2022, Jesper Öqvist
import argparse
import sys, os, subprocess
import re
import datetime
class Author:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.commits = 0
        self.added = 0
        self.deleted = 0

    def edits(s):
        return s.added + s.deleted

    def report(s, by, totlines):
        metrics = list(map(lambda x: format(x, ','),
                [s.commits, s.added, s.deleted, s.edits()]))
        metrics += ["%.1f" % ((100.0 * s.edits())/totlines)]
        if by == 'name':
            return [s.name] + metrics
        elif by == 'email':
            return [s.email] + metrics
        else:
            return ["%s <%s>" % (s.name, s.email)] + metrics

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
    parser.add_argument('--date',
            help='Date to filter on. Accepts a single date in YYYY-MM-DD format, a closed range in [YYYY-MM-DD;YYYY-MM-DD] format, or an open-ended range in [YYYY-MM-DD;YYYY-MM-DD[ format. Use "now" for today.',
            default=None
            )
    parser.add_argument('--branch',
            help='Branch to count commits on. Default is "master"',
            default='master')

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
    if args.date:
        print(args.date)
        if args.date == 'now':
            args.date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        date_range_pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2});(\d{4}-\d{2}-\d{2})(\]|\[)')
        match = date_range_pattern.match(args.date)
        if match:
            start_date = datetime.datetime.strptime(match.group(1), '%Y-%m-%d')
            end_date = datetime.datetime.strptime(match.group(2), '%Y-%m-%d')

            if match.group(3) == '[':
                end_date = end_date + datetime.timedelta(days=-1)

            if start_date > end_date:
                raise Exception('Start date must be before end date')
            args.date = (start_date, end_date)
        else:
            args.date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
    
   
    
        
    

    # Process commits.
    os.chdir(repo)
    #check if branch exists
    out, err = subprocess.Popen(['git', 'branch', '--list'], stdout=subprocess.PIPE).communicate()

    print(out.decode(encoding='UTF-8').splitlines())
    if args.branch not in [branch.replace("*", "").strip() for branch in out.decode(encoding='UTF-8').splitlines()]:
        raise Exception('Branch %s does not exist' % args.branch)


    revs = subprocess.check_output(['git', 'rev-list', args.branch]).split()
    re_auth = re.compile('^(.+)#(.*)')
    re_edits = re.compile('^(\d+)\s+(\d+)') # Binary files start with - -.
    N = len(revs)
    n = 0
    for rev in revs:
        n += 1
        sys.stderr.write('\rcommit: %d / %d%s' % (n, N, ' '*15))
        out, err = subprocess.Popen(['git', 'show', rev, '--numstat', '--format=%an#%ae#%ad', '--date=short'], stdout=subprocess.PIPE).communicate()
        out = out.decode(encoding='UTF-8')
        lines = out.splitlines()
        auth_line = lines[0]
        date = lines[0].split("#")[-1]
        
        if args.date:
            if isinstance(args.date, tuple):
                if datetime.datetime.strptime(date, '%Y-%m-%d') < args.date[0] or datetime.datetime.strptime(date, '%Y-%m-%d') > args.date[1]:
                    continue
            else:
                if datetime.datetime.strptime(date, '%Y-%m-%d') != args.date:
                    continue

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
    totlines = sum(map(lambda x: x.edits(), authors.values()))
    sortkey = lambda a: a.edits() if args.sort == 'edits' else a.commits
    authors = sorted(authors.values(), key=sortkey, reverse=True)
    if args.limit != None:
        authors = authors[:int(args.limit)]
    if args.output == 'plaintext':
        rows = [['Author','Commits','Inserted','Removed','Total','Percent']]
        lens = [ len(r) for r in rows[0] ]
        for auth in authors:
            row = auth.report(args.by, totlines)
            for i in range(len(lens)):
                lens[i] = max(lens[i], len(row[i]))
            rows += [ row ]
        offs = 0
        for row in rows:
            items = []
            for i in range(len(lens)-1):
                items += f'{row[i]:<{lens[i]+2}}'
            items += row[-1]
            print(''.join(items))
    elif args.output.startswith('tex'):
        if args.output == 'tex':
            print('''\\documentclass[10pt,border=10pt]{standalone}
\\usepackage{booktabs}
\\usepackage{newtxtext}
\\begin{document}''')
        print('''\\begin{tabular}{lrrrrr}
\\toprule
\\emph{Author} & \\emph{Commits} & \\emph{Inserted} & \\emph{Removed} & $\\Sigma\,\\downarrow$ & \\% \\\\
\\midrule''')
        for auth in authors:
            print((' & '.join(auth.report(args.by, totlines)) + ' \\\\'))
        print('''\\bottomrule
\\end{tabular}''')
        if args.output == 'tex':
            print('\\end{document}')
    elif args.output == 'csv':
        for auth in authors:
            print(','.join(auth.report(args.by, totlines)))
    elif args.output == 'alias':
        for auth in authors:
            print('%s = %s' % (auth.email, auth.name))

if __name__ == '__main__':
    main()
