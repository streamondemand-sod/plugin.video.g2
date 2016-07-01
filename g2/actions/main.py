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


from g2.libraries import ui
from g2.libraries import addon
from g2.libraries.language import _

from g2 import providers
from g2 import resolvers

from . import action


@action
def menu():
    ui.addDirectoryItem(_('Movies'), 'movies.menu', 'movies', 'DefaultMovies.png')
    ui.addDirectoryItem(_('My Movies'), 'my.menu', 'mygenesis', 'DefaultVideoPlaylists.png')
    if addon.setting('movie_widget') != '0':
        ui.addDirectoryItem(_('Latest Movies'), 'movies.widget', 'moviesAdded', 'DefaultRecentlyAddedMovies.png')
    ui.addDirectoryItem(_('Tools'), 'tools.menu', 'tools', 'DefaultAddonProgram.png')
    if not len(providers.info(force_refresh=None)) or not len(resolvers.info(force_refresh=None)):
        ui.addDirectoryItem(_('[COLOR red]Install providers and resolvers packages to find video sources[/COLOR]'),
                            'packages.dialog', 'tools', 'DefaultAddonProgram.png', isFolder=False)

    ui.endDirectory()
