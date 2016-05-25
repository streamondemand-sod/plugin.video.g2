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

from lib import ui


_traktMode = platform.setting('trakt_user') != ''
_imdbMode = platform.setting('imdb_user') != ''


# TODO[func]: _()-zation and action-ization
def menu(**kwargs):
    ui.addDirectoryItem(30131, 'tools.settings&query=3.0', 'settings.jpg', 'DefaultAddonProgram.png')
    ui.addDirectoryItem(30132, 'updateLibrary&query=tool', 'update.jpg', 'DefaultAddonProgram.png')
    ui.addDirectoryItem(30133, platform.setting('movie_library'), 'movies.jpg', 'DefaultMovies.png', isAction=False)
    ui.addDirectoryItem(30134, platform.setting('tv_library'), 'tvshows.jpg', 'DefaultTVShows.png', isAction=False)
    if _traktMode:
        ui.addDirectoryItem(30135, 'moviesToLibrary&url=traktcollection', 'moviesTraktcollection.jpg', 'DefaultMovies.png')
        ui.addDirectoryItem(30136, 'moviesToLibrary&url=traktwatchlist', 'moviesTraktwatchlist.jpg', 'DefaultMovies.png')
        ui.addDirectoryItem(30137, 'tvshowsToLibrary&url=traktcollection', 'tvshowsTraktcollection.jpg', 'DefaultTVShows.png')
        ui.addDirectoryItem(30138, 'tvshowsToLibrary&url=traktwatchlist', 'tvshowsTraktwatchlist.jpg', 'DefaultTVShows.png')
    if _imdbMode:
        ui.addDirectoryItem(30139, 'moviesToLibrary&url=imdbwatchlist', 'moviesImdbwatchlist.jpg', 'DefaultMovies.png')
        ui.addDirectoryItem(30140, 'tvshowsToLibrary&url=imdbwatchlist', 'tvshowsImdbwatchlist.jpg', 'DefaultTVShows.png')
    ui.endDirectory()

    
# TODO[func]: _()-zation and action-ization
def downloads(**kwargs):
    movie_downloads = platform.setting('movie_downloads')
    if len(platform.listDir(movie_downloads)[0]) > 0:
        ui.addDirectoryItem(30099, movie_downloads, 'movies.jpg', 'DefaultMovies.png', isAction=False)
    tv_downloads = platform.setting('tv_downloads')
    if len(platform.listDir(tv_downloads)[0]) > 0:
        ui.addDirectoryItem(30100, tv_downloads, 'tvshows.jpg', 'DefaultTVShows.png', isAction=False)
    ui.endDirectory()
