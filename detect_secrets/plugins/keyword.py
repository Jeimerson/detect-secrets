"""
This code was extracted in part from
https://github.com/PyCQA/bandit. Using similar heuristic logic,
we adapted it to fit our plugin infrastructure, to create an organized,
concerted effort in detecting all type of secrets in code.

Copyright (c) 2014 Hewlett-Packard Development Company, L.P.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
from __future__ import absolute_import

import re

from .base import BasePlugin
from detect_secrets.core.potential_secret import PotentialSecret


# Note: All values here should be lowercase
BLACKLIST = (
    'apikey',
    'api_key',
    'pass',
    'password',
    'passwd',
    'private_key',
    'secret',
    'secrete',
    'token',
)
FALSE_POSITIVES = (
    "''",
    "''):",
    '""',
    '""):',
    'false',
    'none',
    'not',
    'password)',
    'password},',
    'true',
)
FOLLOWED_BY_COLON_RE = re.compile(
    # e.g. token:
    r'({})(("|\')?):(\s*?)(("|\')?)([^\s]+)(\5)'.format(
        r'|'.join(BLACKLIST),
    ),
)
FOLLOWED_BY_EQUAL_SIGNS_RE = re.compile(
    # e.g. my_password =
    r'({})([^\s]*?)(\s*?)=(\s*?)(("|\')?)([^\s]+)(\5)'.format(
        r'|'.join(BLACKLIST),
    ),
)
FOLLOWED_BY_QUOTES_AND_SEMICOLON_RE = re.compile(
    # e.g. private_key "something";
    r'({})([^\s]*?)(\s*?)("|\')([^\s]+)(\4);'.format(
        r'|'.join(BLACKLIST),
    ),
)
BLACKLIST_REGEX_TO_GROUP = {
    FOLLOWED_BY_COLON_RE: 7,
    FOLLOWED_BY_EQUAL_SIGNS_RE: 7,
    FOLLOWED_BY_QUOTES_AND_SEMICOLON_RE: 5,
}


class KeywordDetector(BasePlugin):
    """This checks if blacklisted keywords
    are present in the analyzed string.
    """

    secret_type = 'Password'

    def analyze_string(self, string, line_num, filename):
        output = {}

        for identifier in self.secret_generator(
            string,
            is_php_file=filename.endswith('.php'),
        ):
            secret = PotentialSecret(
                self.secret_type,
                filename,
                identifier,
                line_num,
            )
            output[secret] = secret

        return output

    def secret_generator(self, string, is_php_file):
        lowered_string = string.lower()

        for REGEX, group_number in BLACKLIST_REGEX_TO_GROUP.items():
            match = REGEX.search(lowered_string)
            if match:
                lowered_secret = match.group(group_number)

                # ([^\s]+) guarantees lowered_secret is not ''
                if not probably_false_positive(lowered_secret, is_php_file):
                    yield lowered_secret


def probably_false_positive(lowered_secret, is_php_file):
    if (
        'fake' in lowered_secret or
        lowered_secret in FALSE_POSITIVES or
        # If it is a .php file, do not report $variables
        (
            is_php_file and
            lowered_secret[0] == '$'
        )
    ):
        return True

    # No function calls
    try:
        if (
            lowered_secret.index('(') < lowered_secret.index(')')
        ):
            return True
    except ValueError:
        pass

    # Skip over e.g. request.json_body['hey']
    try:
        if (
            lowered_secret.index('[') < lowered_secret.index(']')
        ):
            return True
    except ValueError:
        pass

    return False
