#!/usr/bin/env python
# pwgen
# Generates unique, long, reproducible passwords.
#
# Author:   Benjamin Bengfort <benjamin@bengfort.com>
# Created:  A while ago (see blog post)
#
# Copyright (C) 2016 Bengfort.com
# Licensed as Open Source under an MIT License.
#
# ID: pwgen.py [] benjamin@bengfort.com $

"""
Generates unique, long, reproducible passwords.
"""

##########################################################################
## Imports
##########################################################################

import os
import uuid
import yaml
import base64
import hashlib
import commis
import confire

from commis import color
from getpass import getpass
from datetime import datetime
from commis.exceptions import ConsoleError

##########################################################################
## Program Constants
##########################################################################

VERSION = "pwgen.py v1.1"
EPILOG  = "See http://bit.ly/1ROIahb for more information."
DESCRIPTION = "Generates unique, long, reproducible passwords."


##########################################################################
## Configuration
##########################################################################

class Configuration(confire.Configuration):

    CONF_PATHS = [
        os.path.expanduser('~/.pwgen.yaml')
    ]

    # Should be a hash of the master password salted with the device UUID.
    # If None, then a confirmation is used rather than this check.
    password_master = None

    # Embed the device specific UUID to the password generation
    device = False

    # Default salt for all passwords (overriden via command line)
    salt = ""

    # Timestamp of the last configuration
    last_configured = None


settings = Configuration.load()


##########################################################################
## Password Utilities
##########################################################################

class Utilities(object):
    """
    Mixin to provide utilities to command classes.
    """

    def confirm_password(self, password, confirm):
        """
        Compares the password to the confirmation in two ways.
        """
        # Phase 1: Direct Comparison
        if password == confirm:
            return True

        # Phase 2: Encoded Comparison
        master = self.encode_password(
            "{}{}".format(self.get_device(), password)
        )

        if master == confirm:
            return True

        return False

    def get_device(self):
        return str(uuid.uuid3(uuid.NAMESPACE_OID, str(uuid.getnode())))

    def get_password(self, attempts=0, confirm=settings.password_master):

        password = getpass("Enter master passphrase: ").strip()
        confirm  = confirm or getpass("Enter same passphrase again: ").strip()

        if not self.confirm_password(password, confirm):
            if attempts <= 3:
                print color.format(
                    "Password doesn't match configuration or confirmation, try again.",
                    color.YELLOW
                )
                return self.get_password(attempts+1)
            else:
                raise ConsoleError(
                    "Password attempt maximum, stretch fingers and try again!"
                )

        if not password:
            raise ConsoleError("You must supply a base password for the generator!")
        return password

    def encode_password(self, password):
        """
        The encoding and hashing scheme for passwords. Currently:

            SHA-256 hashing
            Base64 encoding
        """
        return base64.b64encode(hashlib.sha256(password).digest())

##########################################################################
## Commands
##########################################################################

class Generate(commis.Command, Utilities):

    name = 'generate'
    help = 'generate a password for a specific domain'
    args = {
        ('-d', '--device'): {
            'default': settings.device,
            'action': 'store_true',
            'help': 'add device uuid to the password',
        },
        ('-s', '--salt'): {
            'default': settings.salt,
            'help': 'salt or increment to add to password',
        },
        'domain': {
            'nargs': 1,
            'help': 'the domain of the site to generate a password for'
        }
    }
    parents = []

    def handle(self, args):
        """
        Use raw input to collect information from the command line.
        """

        # Create the base password string
        password = "{}{}{}".format(
            args.domain[0],         # the domain (makes password unique to domains)
            args.salt,              # the salt (for inner-domain uniqueness)
            self.get_password()     # the master password (for reproducibility)
        )

        # Check to ensure device specific generation
        if args.device:
            password += self.get_device()

        # Hash and encode the base password
        password = self.encode_password(password)

        return password


class Configure(commis.Command, Utilities):

    name = 'config'
    help = 'configure the password generation using confire'
    args = {
        ('-s', '--show'): {
            'action': 'store_true', 'help': 'print config and exit'
        },
        ('-o', '--output'): {
            'default': settings.CONF_PATHS[0], 'metavar': 'PATH',
            'help': 'location to write the configuration to',
        }
    }

    def handle(self, args):
        if args.show:
            # If we're showing settings, print and exit.
            return str(settings)

        # Construct the master password
        master = "{}{}".format(
            self.get_device(),   # Device specific salt
            self.get_password()  # The master password
        )

        # Update settings
        settings.password_master = self.encode_password(master)
        settings.last_configured = datetime.now()

        # Write the path to disk
        with open(args.output, 'w') as f:
            yaml.dump(dict(settings.options()), f, indent=2, default_flow_style=False)

        return "Configured settings in {}".format(args.output)


##########################################################################
## Utility
##########################################################################

class PasswordUtility(commis.ConsoleProgram):

    description = color.format(DESCRIPTION, color.CYAN)
    epilog      = color.format(EPILOG, color.MAGENTA)
    version     = color.format(VERSION, color.CYAN)

    @classmethod
    def load(klass):
        utility = klass()
        utility.register(Generate)
        utility.register(Configure)
        return utility


if __name__ == "__main__":
    app = PasswordUtility.load()
    app.execute()
