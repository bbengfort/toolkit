#!/usr/bin/env python
# requires
# Creates a requirements.txt file using pip freeze.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Fri Jan 22 08:50:31 2016 -0500
#
# Copyright (C) 2016 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: requires.py [] benjamin@bengfort.com $

"""
Creates a requirements.txt file with pip freeze, but does a better job at
dealing with commented packages in the freeze file.
"""

##########################################################################
## Imports
##########################################################################

import os
import pip
import sys
import shutil
import argparse

from pip.operations import freeze
from platform import python_version as pyvers

##########################################################################
## Command Description
##########################################################################

DESCRIPTION = "Creates better requirements.txt files using pip freeze."
EPILOG      = "An alternative is to use pip freeze -r requirements.txt"
VERSION     = "requires v1.0 | pip v{} | python v{}".format(pip.__version__, pyvers())

ARGUMENTS   = {
    ('-o', '--output'): {
        'metavar': 'PATH',
        'default': sys.stdout,
        'type': argparse.FileType('w'),
        'help': 'specify a path to write freeze file to',
    },
    'requirements': {
        'nargs': '?',
        'default': 'requirements.txt',
        'help': 'text file containing requirements',
    },
}


##########################################################################
## Primary Functionality
##########################################################################

# Arguments that may be in the requirements.txt
reqargs = (
    '-r', '--requirement',
    '-Z', '--always-unzip',
    '-f', '--find-links',
    '-i', '--index-url',
    '--extra-index-url',
)

# Parsable operators for semantic versioning
operators = ("==", ">=", ">", "!=", "~=", "<", "<=")


def parse(dep):
    """
    Parses a dependency string and returns the name and the part.
    """

    if dep.startswith("-e") or dep.startswith("--editable"):
        if dep.startswith('-e'):
            name = line[2:].strip()
        else:
            name = line[len('--editable'):].strip().lstrip('=')

        return name, dep

    for operator in operators:
        if operator in dep:
            return dep.split(operator, 1)[0].strip(), dep

    return dep, dep


def packages(**kwargs):
    """
    Uses pip freeze to yield a list of packages installed.
    TODO: Directly implement pip freeze: https://github.com/pypa/pip
    """
    for dep in freeze.freeze(**kwargs):
        yield parse(dep)


def requires(args):
    """
    Compares the output of pip freeze with the contents of a requirements
    file and appropriately merges them (including skipping comments).
    """

    # Get the currently installed packages
    installed = dict(packages())
    removed   = [] 

    # If the requirements file exists, begin comparison
    if os.path.exists(args.requirements):
        with open(args.requirements, 'r') as rf:
            for line in rf:
                line = line.strip()

                # Newlines or arguments in the requirements kept as is
                if not line or line.startswith(reqargs):
                    yield line
                    continue

                # Handling commented lines in the requirements file
                if line.startswith("#"):
                    comment = line.lstrip("# ")
                    name, dep = parse(comment)

                    if name in installed:
                        yield "#{}".format(installed.pop(name))
                        continue

                    yield line
                    continue

                # Handle other dependencies in the requirements
                name, dep = parse(line)
                if name in installed:
                    yield installed.pop(name)
                else:
                    removed.append(name)

        # All remaining dependencies are added
        if installed:
            yield "\n## The following requirements were added by pip freeze:"


    # Yield the remaining sorted list of dependencies
    for dep in sorted(installed.values(), key=lambda x: x.lower()):
        yield dep

    # Yield the uninstalled dependencies
    if removed:
        yield "\n## The following requirements are no longer installed:"
        for name in removed: yield "#{}".format(name)


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
    args   = parser.parse_args()
    output = list(requires(args))
    args.output.write("\n".join(output)+"\n")

    # Exit successfully
    parser.exit(0)

if __name__ == '__main__':
    main(*sys.argv[1:])
