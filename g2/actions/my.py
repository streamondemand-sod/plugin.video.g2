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

from lib import ui


_trakt_user = platform.setting('trakt_user') if platform.setting('trakt_enabled') else ''
_imdb_user = platform.setting('imdb_user')


# (fixme) intl
def menu(action, **kwargs):
    if _trakt_user:
        ui.addDirectoryItem(30081, 'movies.movielist&url='+dbs.url('movies_collection{trakt_user_id}', trakt_user_id=_trakt_user, quote_plus=True), 'moviesTraktcollection.jpg', 'DefaultMovies.png',
            context=(30191, 'moviesToLibrary&url=traktcollection'))
        ui.addDirectoryItem(30082, 'movies.movielist&url='+dbs.url('movies_watchlist{trakt_user_id}', trakt_user_id=_trakt_user, quote_plus=True), 'moviesTraktwatchlist.jpg', 'DefaultMovies.png',
            context=(30191, 'moviesToLibrary&url=traktwatchlist'))
        ui.addDirectoryItem(30083, 'movies.movielist&url='+dbs.url('movies_recommendations{}', quote_plus=True), 'movies.jpg', 'DefaultMovies.png')
        ui.addDirectoryItem(30084, 'movies.movielist&url='+dbs.url('movies_ratings{trakt_user_id}', trakt_user_id=_trakt_user, quote_plus=True), 'movies.jpg', 'DefaultMovies.png')

    if _imdb_user:
        ui.addDirectoryItem(30091, 'movies&url=imdbwatchlist', 'moviesImdbwatchlist.jpg', 'DefaultMovies.png', context=(30191, 'moviesToLibrary&url=imdbwatchlist'))

    if _trakt_user or _imdb_user:
        ui.addDirectoryItem(_('Movie Lists'), 'movies.userlists', 'movieUserlists.jpg', 'DefaultMovies.png')

    if platform.setting('downloads'):
        ui.addDirectoryItem(30098, 'download.menu', 'downloads.jpg', 'DefaultFolder.png')

    ui.endDirectory()
