#!/usr/bin/env python3
# Copyright (c) 2018-2025, Jesper Öqvist
import argparse
import multiprocessing as mp
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Optional

from author import Author, Authors
from enums import CollateBy, Column, OutputFormat
from output_formats import output_csv, output_plaintext, output_tex

strptime = datetime.strptime


class NumStatGetter:
    def __init__(self, commit_hashes: list[str]):
        self.commit_hashes = commit_hashes
        self.completed = 0

    def get_numstats_for_hash(self, commit: str, queue: Optional[mp.Queue] = None) -> list[str]:
        out, _ = subprocess.Popen(
            ["git", "show", commit, "--numstat", "--format=%an#%ae#%ad", "--date=short"], stdout=subprocess.PIPE
        ).communicate()
        out = out.decode(encoding="UTF-8")

        if queue is not None:
            # We send a dummy message to the queue to indicate that this commit has been processed.
            queue.put("done")
        return out.splitlines()

    @staticmethod
    def progress_listener(queue: mp.Queue, number_of_commits: int):
        sys.stderr.write("Counting lines in commits:\n")
        for i in range(number_of_commits):
            sys.stderr.write("\rcommit: %d / %d%s" % (i, number_of_commits, " " * 15))
            queue.get()
        sys.stderr.write("\r%s\r" % (" " * 25))

    def get_numstats_multiprocessing(self) -> list[list[str]]:
        cpu_count = os.cpu_count()
        if cpu_count is None:
            # Apparently os.cpu_count() can return None. In that case we default to single threaded execution.
            return self.get_numstats_singlethreaded()

        # When we run things in parallel, the individual processes doesn't know about each other,
        # and we can't use a simple counter.
        # Instead, we have each process report when it is done to a queue, and we have a separate
        # process that listens to the queue and prints the progress.
        manager = mp.Manager()
        queue = manager.Queue()
        progress_bar = mp.Process(
            target=self.progress_listener,
            args=(
                queue,
                len(self.commit_hashes),
            ),
        )
        progress_bar.start()

        # We use cpu_count - 4 to leave some CPU cores free for the system.
        with mp.Pool(cpu_count - 4) as pool:
            numstats = pool.starmap(self.get_numstats_for_hash, [(commit, queue) for commit in self.commit_hashes])

        progress_bar.join()
        return numstats

    def get_numstats_singlethreaded(self) -> list[list[str]]:
        numstats = []
        N = len(self.commit_hashes)
        for i, commit in enumerate(self.commit_hashes):
            sys.stderr.write("\rcommit: %d / %d%s" % (i, N, " " * 15))
            numstats.append(self.get_numstats_for_hash(commit))
        return numstats


def gather_data(args: argparse.Namespace, repo: str, alias: dict[str, str]) -> Authors:
    os.chdir(repo)

    # Check if branch exists
    out, _ = subprocess.Popen(["git", "branch", "--list"], stdout=subprocess.PIPE).communicate()
    allbranches = [branch.replace("*", "").strip() for branch in out.decode(encoding="UTF-8").splitlines()]

    if args.branch not in allbranches:
        raise Exception("Branch %s does not exist" % args.branch)

    authors: Authors = Authors(args.by)

    re_edits = re.compile(r"^(\d+)\s+(\d+)")  # Binary files start with - -.
    cmd = ["git", "rev-list"]
    if args.since:
        cmd += [f"--since-as-filter={args.since}"]
    if args.until:
        cmd += [f"--until={args.until}"]
    if args.max_count:
        cmd += [f"--max-count={args.max_count}"]
    cmd += [args.branch]
    commit_hashes_reverse = subprocess.check_output(cmd).decode().split()

    helper = NumStatGetter(commit_hashes_reverse)
    if args.multiprocessing:
        liness = helper.get_numstats_multiprocessing()
    else:
        liness = helper.get_numstats_singlethreaded()

    for lines in liness:
        # for rev in revs:
        name, email, date = lines[0].split("#")

        author = authors.add_get_author(alias.get(email, name), email, date)

        if strptime(date, "%Y-%m-%d") < strptime(author.first_date, "%Y-%m-%d"):
            author.first_date = date
        if strptime(date, "%Y-%m-%d") > strptime(author.last_date, "%Y-%m-%d"):
            author.last_date = date

        author.commits += 1
        for ln in lines[1:]:
            edits = re_edits.match(ln)
            if edits:
                author.added += int(edits.group(1))
                author.deleted += int(edits.group(2))
    sys.stderr.write("\r%s\r" % (" " * 25))
    return authors


def output_data(args: argparse.Namespace, authors: Authors):
    totlines = sum(map(lambda x: x.edits(), authors.values()))

    def sortkey(author: Author):
        if args.sort == "edits":
            return author.edits()
        else:
            return author.commits

    authors_list = sorted(authors.values(), key=sortkey, reverse=True)
    keys = list(args.columns)
    for i, k in enumerate(keys):
        if k == Column.AUTHOR:
            if args.by == CollateBy.BOTH:
                keys[i] = Column.NAME_EMAIL
            else:
                keys[i] = args.by

    if args.limit is not None:
        authors_list = authors_list[: int(args.limit)]
    if args.output == OutputFormat.PLAINTEXT:
        output_plaintext(keys, authors_list, totlines)
    elif args.output.startswith("tex"):
        output_tex(keys, authors_list, totlines, args.output)
    elif args.output == OutputFormat.CSV:
        output_csv(keys, authors_list, totlines)
    elif args.output == OutputFormat.ALIAS:
        for author in authors_list:
            print("%s = %s" % (author.email, author.name))


def main():
    parser = argparse.ArgumentParser(
        description="Counts lines in git project.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # Show default values in help text.
    )
    parser.add_argument("repository", type=str, help="The git repository to count lines in.")
    parser.add_argument(
        "--by",
        type=CollateBy,
        choices=CollateBy,
        default=CollateBy.BOTH,
        help="Collate by author name, email, or both",
    )
    parser.add_argument(
        "--output",
        choices=OutputFormat,
        default=OutputFormat.PLAINTEXT,
        help="Select output format.",
        type=OutputFormat,
    )
    parser.add_argument("--limit", help="Maximum number of output rows", type=int)
    parser.add_argument("--alias", help="File mapping emails to author names")
    parser.add_argument("--sort", choices=["edits", "commits"], default="edits", help="Column to sort on")
    parser.add_argument(
        "--since", "--after", help="Limit statistics to commits more recent than this date", default=None
    )
    parser.add_argument("--until", "--before", help="Limit statistics to commits older than this date", default=None)
    parser.add_argument("--branch", help="Branch to count commits on", default="master")
    parser.add_argument("--max-count", "-n", help="Limit to the MAX_COUNT most recent commits")
    parser.add_argument(
        "--columns",
        type=Column,
        default=None,
        nargs="*",
        help="Comma-separated list of column to display.",
        choices=sorted(Column),
    )
    parser.add_argument(
        "--multiprocessing",
        action="store_true",
        help="Use multiprocessing to speed up the counting of lines.",
    )

    args = parser.parse_args()

    if args.columns is None:
        if args.output == OutputFormat.CSV:
            args.columns = [Column.AUTHOR, Column.COMMITS, Column.ADDED, Column.DELETED, Column.EDITS, Column.PERCENT]
        else:
            args.columns = [
                Column.AUTHOR,
                Column.COMMITS,
                Column.ADDED,
                Column.DELETED,
                Column.EDITS,
                Column.FIRST_DATE,
                Column.LAST_DATE,
            ]

    repo: str = args.repository
    if not os.path.isdir(repo):
        # Check out the repo to local directory.
        sys.stderr.write(f"Cloning {repo} into ./repo\n")
        if not os.path.isdir("repo"):
            exit_code = subprocess.call(["git", "clone", repo, "repo"])
            if exit_code != 0:
                raise Exception("Failed to fetch git repository %s" % repo)
        repo = "repo"

    # Read author alias file:
    alias: dict[str, str] = {}
    if args.alias:
        with open(args.alias, "r") as fp:
            for ln in fp.readlines():
                email, name = ln.split("=")
                alias[email.strip()] = name.strip()

    data = gather_data(args, repo, alias)
    output_data(args, data)


if __name__ == "__main__":
    main()
