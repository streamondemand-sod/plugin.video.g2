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


PACKAGES_DIRECTORY_URLS = ['http://j0rdyz65.github.io/packages.html']
"""List of URL where the addon package directories can be found"""

DEFAULT_PACKAGE_PRIORITY = 10
"""Package priority unless redefined by the package itself or configured by the user"""

METADATA_CACHE_LIFETIME = (30*24)
"""Cache lifetime in hours for the video metadata"""

RESOLVER_TIMEOUT = 10
"""Maximum time in seconds to wait for a resolver to provide a result"""

MIN_STREAM_SIZE = 1024 * 1024
"""Minimum stream size in bytes to consider it a valid video stream"""

BOOKMARK_THRESHOLD = 2
"""Minimum percentage to pass to save a bookmark"""

WATCHED_THRESHOLD = 90
"""Minimum percentage to pass to update the video watched status"""

# (fixme) check w/ boogiepop the feasibility to use this
HOST_IMAGES = "https://offshoregit.com/boogiepop/dataserver/ump/images/"
"""Repository for the hosts icons"""

TRAKT_CLIENT_ID = 'c67fa3018aa2867c183261f4b2bb12ebb606c2b3fbb1449e24f2fbdbc3a8ffdb'
"""Trakt plugin.video.g2 client id -- do not change unless you know what you are doing!!! :)"""

TRAKT_MAX_RECOMMENDATIONS = 60
"""Trakt maximum number of recommendations (the maximum value is 100)"""

TMDB_INCLUDE_ADULT = False
"""Self explaining, isn't? :)"""

TMDB_APIKEY = 'f7f51775877e0bb6703520952b3c7840'
"""This is the TMDB API key stolen from other addons.
Actually each user should configure his own key.
This policy might be enforced in the official releases."""

TVDB_APIKEY = 'FA1E453AC1E9754C'
"""TVDB API key"""

MAX_CONCURRENT_THREADS = 10
"""All the modules forking parallel threads to speedup their activity should respect
this limit so that the HW resources for a particular platform are not depleted."""
