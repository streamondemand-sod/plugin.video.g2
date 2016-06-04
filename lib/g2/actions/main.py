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


# TODO[code]: rename to main.menu
def menu(action, **kwargs):
    ui.addDirectoryItem(_('Movies'), 'movies.menu', 'movies.jpg', 'DefaultMovies.png')
    ui.addDirectoryItem(_('My Genesis'), 'mygenesis.menu', 'mygenesis.jpg', 'DefaultVideoPlaylists.png')
    if platform.setting('movie_widget') != '0':
        # TODO[UI]: show which provider is giving the list (see movies)
        ui.addDirectoryItem(_('Latest Movies'), 'movies.widget', 'moviesAdded.jpg', 'DefaultRecentlyAddedMovies.png')
    ui.addDirectoryItem(_('Tools'), 'tools.menu', 'tools.jpg', 'DefaultAddonProgram.png')
    ui.endDirectory(action)
