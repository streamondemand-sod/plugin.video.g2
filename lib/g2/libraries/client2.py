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


import requests
from BeautifulSoup import BeautifulSoup


def get(*args, **kwargs):
    bs_body = kwargs.get('bs_body')
    if 'bs_body' in kwargs:
        del kwargs['bs_body']

    res = requests.get(*args, **kwargs)
    res.raise_for_status()
    if bs_body:
        # For BS 3, in BS 4, entities get decoded automatically.
        res.bs_body = BeautifulSoup(res.content, convertEntities=BeautifulSoup.HTML_ENTITIES)

    return res
