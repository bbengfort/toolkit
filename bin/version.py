#!/usr/bin/env python
# version
# Scans the local directory if it's a git repository and adds the ID line.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Mon Mar 07 17:53:36 2016 -0500
#
# Copyright (C) 2016 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: version.py [] benjamin@bengfort.com $

"""
Scans the local directory if it's a git repository and adds the ID line.
"""

##########################################################################
## Imports
##########################################################################

import re
import os
import sys
import git
import argparse
import fileinput

##########################################################################
## Command Description
##########################################################################

DESCRIPTION = "Writes the $ID strings to files in the local git repository."
EPILOG      = "This is one of the first Bengfort Toolkit commands."
VERSION     = "version v1.0"

ARGUMENTS   = {
    ('-U', '--user'): {
        'metavar': 'email',
        'default': None,
        'help': 'overwrite the user email to write to',
    },
    ('-o', '--output'): {
        'metavar': 'PATH',
        'default': sys.stdout,
        'type': argparse.FileType('w'),
        'help': 'path to write out data to (stdout by default)'
    },
    ('-b', '--branch'): {
        'default': 'master',
        'help': 'the branch to list commits from'
    },
    ('-m', '--modify'): {
        'action': 'store_true',
        'default': False,
        'help': 'modify files in place to reset their versions'
    },
    '-n': {
        'metavar': 'NUM',
        'dest': 'num_lines',
        'type': int,
        'default': 20,
        'help': 'maximum number of header lines to search for ID string.'
    },
    'repo': {
        'nargs': '?',
        'default': os.getcwd(),
        'help': 'path to repository to add version ID strings',
    },
}

##########################################################################
## Primary Functionality
##########################################################################

IDRE = re.compile(r'^#\s*ID:\s+([\w\.\-]+)\s+\[([a-f0-8]*)\]\s+([\w\@\.\+\-]*)\s+\$\s*$', re.I)

def versionize(args):
    """
    Primary utility for performing the versionization.
    """
    try:
        path = os.path.abspath(args.repo)

        if not os.path.isdir(path):
            raise Exception("'{}' is not a directory!".format(args.repo))

        repo = git.Repo(path)
    except git.InvalidGitRepositoryError:
        raise Exception("'{}' is not a Git repository!".format(args.repo))


    # Construct the path version tree.
    versions = {}
    for commit in repo.iter_commits(args.branch):
        for blob in commit.tree.traverse():
            versions[blob.abspath] = commit

    # Track required modifications
    output = []

    # Walk the directory path
    for root, dirs, files in os.walk(path):

        # Ignore hidden directories (.git)
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for name in files:
            name = os.path.join(root, name)
            if name not in versions: continue
            output.append(
                read_head(name, versions[name], maxlines=args.num_lines)
            )

    # Remove any non-matched files.
    output = filter(None, output)

    # Make the modifications if the args specifies to
    if args.modify:
        for path, vers in output:
            modify_inplace(path, vers)

    # Return the output
    return [
        "{}  {}".format(path, vers)
        for path, vers in output
    ] if output else ["No files require an ID header."]


def read_head(path, commit, maxlines=None):
    """
    Reads the first maxlines of the file (or all lines if None) and looks
    for the version string. If it exists, it replaces it with the commit
    and author information.
    """

    with open(path, 'r') as f:
        for idx, line in enumerate(f.readlines()):
            if maxlines and idx >= maxlines:
                break

            match = IDRE.match(line)
            if match and not match.groups()[1]:
                vers = "# ID: {} [{}] {} $".format(
                    os.path.basename(path), commit.hexsha[:7], commit.author.email
                )
                return path, vers


def modify_inplace(path, vers):
    """
    Modifies the ID line by writing all lines except the match line.
    """
    matched = False
    for line in fileinput.input(path, inplace=1):
        if not matched and IDRE.match(line):
            matched = True
            sys.stdout.write(vers + "\n")
        else:
            sys.stdout.write(line)


##########################################################################
## Main Method
##########################################################################

def main(*args):

    # Construct the argument parser
    parser = argparse.ArgumentParser(
        description=DESCRIPTION, epilog=EPILOG, version=VERSION
    )

    # Add the arguments from the definition above
    for keys, kwargs in ARGUMENTS.items():
        if not isinstance(keys, tuple):
            keys = (keys,)
        parser.add_argument(*keys, **kwargs)

    # Handle the input from the command line
    # try:
    args   = parser.parse_args()
    output = list(versionize(args))
    args.output.write("\n".join(output)+"\n")
    # except Exception as e:
    #     parser.error(str(e))

    # Exit successfully
    parser.exit(0)

if __name__ == '__main__':
    main(*sys.argv[1:])
