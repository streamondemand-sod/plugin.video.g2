# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2016-2017 J0rdyZ65

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


from g2.libraries import addon
from g2.libraries.language import _
from g2 import dbs

from .lib import uid
from . import action


@action
def menu():
    trakt_user = addon.setting('trakt_user')
    imdb_user = addon.setting('imdb_user')
    if not trakt_user or addon.setting('trakt_enabled') != 'true':
        uid.additem(_('Configure your Trakt account'), 'tools.settings&category=1',
                    'moviesTraktcollection', 'DefaultMovies.png', isFolder=False)
    else:
        url = dbs.resolve('movies_collection{trakt_user_id}', trakt_user_id=trakt_user, quote_plus=True)
        if url:
            uid.additem(_('[B]TRAKT[/B] : Collection'), 'movies.movielist&url='+url,
                        'moviesTraktcollection', 'DefaultMovies.png')
        url = dbs.resolve('movies_watchlist{trakt_user_id}', trakt_user_id=trakt_user, quote_plus=True)
        if url:
            uid.additem(_('[B]TRAKT[/B] : Watchlist'), 'movies.movielist&url='+url,
                        'moviesTraktwatchlist', 'DefaultMovies.png')
        url = dbs.resolve('movies_ratings{trakt_user_id}', trakt_user_id=trakt_user, quote_plus=True)
        if url:
            uid.additem(_('[B]TRAKT[/B] : Ratings'), 'movies.movielist&url='+url,
                        'moviesTraktrated', 'DefaultMovies.png')

        url = dbs.resolve('movies_recommendations{}', quote_plus=True)
        if url:
            uid.additem(_('[B]TRAKT[/B] : Recommendations'), 'movies.movielist&url='+url,
                        'moviesTraktrecommendations', 'DefaultMovies.png')

        uid.additem(_('[B]TRAKT[/B] : Lists by {trakt_user}').format(trakt_user=trakt_user),
                    'movies.lists&kind_user_id=trakt_user_id&kind_list_id=trakt_list_id&user_id=%s'%trakt_user,
                    'movieUserlists', 'DefaultMovies.png')

    if not imdb_user:
        uid.additem(_('Configure your IMDB account'), 'tools.settings&category=1',
                    'movieUserlists', 'DefaultMovies.png', isFolder=False)
    else:
        imdb_nickname = addon.setting('imdb_nickname') or imdb_user
        uid.additem(_('[B]IMDB[/B] : Lists by {imdb_nickname}').format(imdb_nickname=imdb_nickname),
                    'movies.lists&kind_user_id=imdb_user_id&kind_list_id=imdb_list_id&user_id=%s'%imdb_user,
                    'movieUserlists', 'DefaultMovies.png')

    if addon.setting('downloads'):
        uid.additem(_('Downloads'), 'download.menu', 'downloads', 'DefaultFolder.png')
    else:
        uid.additem(_('Configure the download directory'), 'tools.settings&category=0',
                    'downloads', 'DefaultFolder.png', isFolder=False)

    uid.finish()
