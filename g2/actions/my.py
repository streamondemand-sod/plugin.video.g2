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


from g2.libraries import platform
from g2.libraries.language import _
from g2 import dbs

from .lib import ui
from . import action


@action
def menu():
    trakt_user = platform.setting('trakt_user')
    imdb_user = platform.setting('imdb_user')
    if not trakt_user or platform.setting('trakt_enabled') != 'true':
        ui.addDirectoryItem(_('Configure your Trakt account to unlock new functions'), 'tools.settings&category=1&setting=1',
                            'moviesTraktcollection.jpg', 'DefaultMovies.png')
    else:
        url = dbs.resolve('movies_collection{trakt_user_id}', trakt_user_id=trakt_user, quote_plus=True)
        if url:
            ui.addDirectoryItem(_('[B]TRAKT[/B] : Collection'), 'movies.movielist&url='+url,
                                'moviesTraktcollection.jpg', 'DefaultMovies.png')
        url = dbs.resolve('movies_watchlist{trakt_user_id}', trakt_user_id=trakt_user, quote_plus=True)
        if url:
            ui.addDirectoryItem(_('[B]TRAKT[/B] : Watchlist'), 'movies.movielist&url='+url,
                                'moviesTraktwatchlist.jpg', 'DefaultMovies.png')
        url = dbs.resolve('movies_ratings{trakt_user_id}', trakt_user_id=trakt_user, quote_plus=True)
        if url:
            ui.addDirectoryItem(_('[B]TRAKT[/B] : Ratings'), 'movies.movielist&url='+url,
                                'movies.jpg', 'DefaultMovies.png')

    url = dbs.resolve('movies_recommendations{}', quote_plus=True)
    if url:
        ui.addDirectoryItem(_('[B]TRAKT[/B] : Recommendations'), 'movies.movielist&url='+url,
                            'movies.jpg', 'DefaultMovies.png')

    if trakt_user:
        ui.addDirectoryItem(_('[B]TRAKT[/B] : Lists by %s')%trakt_user,
                            'movies.lists&kind_user_id=trakt_user_id&kind_list_id=trakt_list_id&user_id=%s'%trakt_user,
                            'movieUserlists.jpg', 'DefaultMovies.png')
    if imdb_user:
        # (fixme) should be the nickname
        ui.addDirectoryItem(_('[B]IMDB[/B] : Lists by %s')%imdb_user,
                            'movies.lists&kind_user_id=imdb_user_id&kind_list_id=imdb_list_id&user_id=%s'%imdb_user,
                            'movieUserlists.jpg', 'DefaultMovies.png')

    if platform.setting('downloads'):
        ui.addDirectoryItem(_('Downloads'), 'download.menu', 'downloads.jpg', 'DefaultFolder.png')

    ui.endDirectory()
