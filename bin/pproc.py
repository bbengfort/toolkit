#!/usr/bin/env python3
# pproc
# Runs multiple subprocesses in parallel, serializing stdout.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  Wed Jun 14 15:20:05 2017 -0400
#
# Copyright (C) 2017 Bengfort.com
# For license information, see LICENSE.txt
#
# ID: pproc.py [] benjamin@bengfort.com $

"""
Runs multiple subprocesses in parallel, serializing stdout.
See: https://stackoverflow.com/questions/9743838/python-subprocess-in-parallel
"""

##########################################################################
## Imports
##########################################################################

import shlex
import argparse

from select import select
from subprocess import Popen, PIPE

##########################################################################
## Command Description
##########################################################################

DESCRIPTION = "Run multiple subprocesses concurrently, serializing stdout"
EPILOG      = "This is a Bengfort toolkit command"
VERSION     = "%(prog)s v1.0"


##########################################################################
## Command Functions
##########################################################################

def tokenize(commands):
    for command in commands:
        yield shlex.split(command)


def pprint(proc):
    # pretty print the standard out of the process
    msg = "[{}] out: {}".format(p.pid, p.stdout.read())
    print(msg, end="")


def execute(commands, debug=False, timeout=0.1):
    # Use shlex to tokenize commands
    commands = list(tokenize(commands))

    # If debug, print out the commands and return
    if debug:
        for command in commands:
            print(repr(command))
        return

    # Popen keyword arguments and defaults
    kwds = {
        "stdout": PIPE,
        "bufsize": 1,
        "close_fds": True,
        "universal_newlines": True,
    }

    # Build the process list
    procs = [Popen(cmd, **kwds) for cmd in commands]

    # Join on proesses, reading stdout as we can
    while procs:
        # Remove finished processes from the list
        for p in procs:
            if p.poll() is not None:           # process ended
                print(p.stdout.read(), end='') # print remaining stdout
                p.stdout.close()               # clean up file descriptors
                procs.remove(p)                # remove the process

        # Attempt to read stdout where we can
        rlist = select([p.stdout for p in procs], [], [], timeout)[0]
        for f in rlist:
            print(f.readline(), end='')


##########################################################################
## Main Method
##########################################################################

if __name__ == '__main__':

    # Construct the argument parser
    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)

    # Add the arguments
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument(
        '-t', '--timeout', type=float, metavar="SEC", default=0.1,
        help='specify the select timeout for sync',
    )
    parser.add_argument(
        '-d', '--debug', action='store_true', default=False,
        help='print the parsed commands and exit',
    )
    parser.add_argument(
        'commands', type=str, nargs="+", metavar="command", help=(
            "command and arguments to execute in parallel -- ensure that a "
            "single command is surrounded in quotes, correctly escaped "
            "use the -d flag to show the command being executed"
        )
    )

    # Handle the input from the command line
    try:
        args = parser.parse_args()
        execute(args.commands, debug=args.debug, timeout=args.timeout)
        parser.exit(0)
    except Exception as e:
        parser.error(str(e))
