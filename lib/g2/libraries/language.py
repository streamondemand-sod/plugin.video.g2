# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016 J0rdyZ65

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re

import xbmc
import xbmcaddon

from g2.libraries import log


_addon = xbmcaddon.Addon()
_msgs_codes = {}


def _read_msgs():
    pofile = os.path.join(_addon.getAddonInfo('path'), 'resources', 'language', 'English', 'strings.po')
    with open(pofile, 'r') as po:
        msgctxt = None
        for s in po:
            try:
                # msgctxt "#30006"
                msgctxt = int(re.match(r'msgctxt\s*"#(\d+)"', s).group(1))
                continue
            except Exception:
                pass
            try:
                # msgid "Latest Episodes"
                msgid = re.match(r'msgid\s*"([^"]+)"', s).group(1)
                if not msgid: raise
                if msgctxt:
                    if msgid not in _msgs_codes:
                        _msgs_codes[msgid] = []
                    _msgs_codes[msgid].append(msgctxt)
                continue
            except Exception:
                pass
            if re.match(r'\s*$', s):
                msgctxt = None

    for msgid, codes in _msgs_codes.iteritems():
        if len(codes) > 1:
            # TODO[code]: remove all duplicated strings!!!
            log.debug('lang: "%s": multiple codes: %s'%(msgid, ', '.join(map(lambda x: str(x), codes))))


if not len(_msgs_codes): _read_msgs()


def _(msgid):
    if type(msgid) == int:
        msgid = _addon.getLocalizedString(msgid)
    elif msgid in _msgs_codes:
        msgid = _addon.getLocalizedString(_msgs_codes[msgid][0])
    else:
        msgid = str(msgid)
    return msgid.encode('utf-8')


def msgcode(msgid):
    return _msgs_codes[msgid][0] if msgid in _msgs_codes else 0


def name(language):
    return xbmc.convertLanguage(language, xbmc.ENGLISH_NAME)
