# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright (C) 2015 lambda
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


import json
import urllib

from g2.libraries import ui
from g2.libraries import log
from g2.libraries import addon
from g2.libraries.language import _
from g2 import dbs

from . import action, busyaction


@action
def menu():
    if dbs.resolve('movies_recently_added{}'):
        db_provider = dbs.resolve('movies_recently_added{}', return_db_provider=True)
        ui.addDirectoryItem(_('Latest Movies')+' ['+db_provider.upper()+']',
                            'movies.movielist&url='+dbs.resolve('movies_recently_added{}', quote_plus=True),
                            'moviesAdded', 'DefaultRecentlyAddedMovies.png')

    ui.addDirectoryItem(_('Search by Title'), 'movies.searchbytitle', 'movieSearch', 'DefaultMovies.png', isFolder=False)
    ui.addDirectoryItem(_('Search by Person'), 'movies.searchbyperson', 'moviePerson', 'DefaultMovies.png', isFolder=False)
    ui.addDirectoryItem(_('Search by Year'), 'movies.searchbyyear', 'movieYears', 'DefaultYear.png', isFolder=False)

    ui.addDirectoryItem(_('Genres'), 'movies.genres', 'movieGenres', 'DefaultGenre.png')
    ui.addDirectoryItem(_('Certificates'), 'movies.certifications', 'movieCertificates', 'DefaultMovies.png')

    if dbs.resolve('movies_featured{}'):
        ui.addDirectoryItem(_('Featured'), 'movies.movielist&url='+dbs.resolve('movies_featured{}', quote_plus=True),
                            'movies', 'DefaultRecentlyAddedMovies.png')
    if dbs.resolve('movies_trending{}'):
        ui.addDirectoryItem(_('People Watching'), 'movies.movielist&url='+dbs.resolve('movies_trending{}', quote_plus=True),
                            'moviesTrending', 'DefaultRecentlyAddedMovies.png')
    if dbs.resolve('movies_popular{}'):
        ui.addDirectoryItem(_('Most Popular'), 'movies.movielist&url='+dbs.resolve('movies_popular{}', quote_plus=True),
                            'moviesPopular', 'DefaultMovies.png')
    if dbs.resolve('movies_toprated{}'):
        ui.addDirectoryItem(_('Most Voted'), 'movies.movielist&url='+dbs.resolve('movies_toprated{}', quote_plus=True),
                            'moviesViews', 'DefaultMovies.png')
    if dbs.resolve('movies_boxoffice{}'):
        ui.addDirectoryItem(_('Box Office'), 'movies.movielist&url='+dbs.resolve('movies_boxoffice{}', quote_plus=True),
                            'moviesBoxoffice', 'DefaultMovies.png')
    if dbs.resolve('movies_oscar{}'):
        ui.addDirectoryItem(_('Oscar Winners'), 'movies.movielist&url='+dbs.resolve('movies_oscar{}', quote_plus=True),
                            'moviesOscars', 'DefaultMovies.png')
    if dbs.resolve('movies_theaters{}'):
        ui.addDirectoryItem(_('In Theaters'), 'movies.movielist&url='+dbs.resolve('movies_theaters{}', quote_plus=True),
                            'moviesTheaters', 'DefaultRecentlyAddedMovies.png')
    ui.endDirectory()


@action
def searchbytitle():
    query = ui.keyboard(_('Title to search'))
    if query:
        url = dbs.resolve('movies{title}', title=query, quote_plus=True)
        ui.refresh('movies.movielist', url=url)


@action
def searchbyperson():
    query = ui.keyboard(_('Person to search'))
    if query:
        url = dbs.resolve('persons{name}', name=query, quote_plus=True)
        ui.refresh('movies.personlist', url=url)


@action
def searchbyyear():
    query = ui.keyboard(_('Year'))
    if query:
        url = dbs.resolve('movies{year}', year=query, quote_plus=True)
        ui.refresh('movies.movielist', url=url)


@action
def genres():
    items = dbs.genres()
    for i in items:
        image = i.get('image', '0')
        if image == '0':
            # (fixme) Need a table mapping genre 'id' to different icons
            image = 'DefaultGenre.png'
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{genre_id}', genre_id=i['id']),
            'image': image,
        })
    _add_directory(items)


@action
def certifications():
    items = dbs.certifications()
    items = sorted(items, key=lambda c: c['order'])

    for i in items:
        image = i.get('image', '0')
        if image == '0':
            # (fixme) Need a table mapping certification 'name' to different icons
            image = 'movieCertificates.jpg'
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{certification}', certification=i['name']),
            'image': image,
        })
    _add_directory(items)


@action
def movielist(url):
    items = dbs.movies(url)
    if not items:
        ui.infoDialog(_('No results'))
        return
    for i in items:
        i['next_action'] = 'movies.movielist'
    dbs.meta(items)
    _add_movie_directory(items)


@action
def personlist(url):
    items = dbs.persons(url)
    if not items:
        ui.infoDialog(_('No results'))
        return
    for i in items:
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{person_id}', person_id=i['id']),
            'next_action': 'movies.personlist',
        })
    _add_directory(items, is_person=True)


@action
def lists(kind_user_id='trakt_user_id', kind_list_id='trakt_list_id', user_id=''):
    args = {kind_user_id: user_id}
    items = dbs.lists('lists{%s}'%kind_user_id, **args)
    if not items:
        items = []
    addon_userlists = ui.media('movieUserlists', 'DefaultVideoPlaylists.png')
    for i in items:
        args[kind_list_id] = i[kind_list_id]
        image = i.get('image', '0')
        if image == '0':
            image = addon_userlists
        poster = i.get('poster')
        if poster == '0':
            poster = addon_userlists
        i.update({
            'action': 'movies.movielist',
            'url': dbs.resolve('movies{%s}{%s}'%(kind_user_id, kind_list_id), **args),
            'image': image,
            'poster': poster,
        })
    if not items:
        ui.infoDialog(_('No results'))
        return
    # (fixme) in lists{} put the meta in 'meta', not 'genre'...
    _add_directory(items, show_genre_as='genre')


@busyaction
def watched(imdb):
    dbs.watched('movie{imdb_id}', True, imdb_id=imdb)
    ui.refresh()


@busyaction
def unwatched(imdb):
    dbs.watched('movie{imdb_id}', False, imdb_id=imdb)
    ui.refresh()


def _add_movie_directory(items):
    if not items:
        return

    addon_poster = ui.addon_poster()
    addon_banner = ui.addon_banner()
    addon_fanart = ui.addon_fanart()
    fanart_enabled = addon.setting('fanart') == 'true'

    for i in items:
        try:
            label = i['name']
            systitle = urllib.quote_plus(i['title'])
            imdb, tmdb, year = i['imdb'], i['tmdb'], i['year']

            poster = i.get('poster', '0')
            if poster == '0':
                poster = addon_poster
            banner = i.get('banner', '0')
            if banner == '0':
                banner = addon_banner if poster == '0' else poster
            fanart = i.get('fanart', '0')
            if fanart == '0':
                fanart = addon_fanart

            meta = dict((k, v) for k, v in i.iteritems() if not v == '0')
            try:
                meta.update({
                    'duration': str(int(meta['duration']) * 60),
                })
            except Exception:
                pass
            sysmeta = urllib.quote_plus(json.dumps(meta))

            url = addon.itemaction('sources.dialog', title=systitle, year=year, imdb=imdb, tmdb=tmdb, meta=sysmeta)

            is_watched = dbs.watched('movie{imdb_id}', imdb_id=imdb)
            if is_watched:
                meta.update({
                    'playcount': 1,
                    'overlay': 7
                })

            cmds = []
            cmds.append((_('Movie information'), 'Action(Info)'))
            if addon.condition('System.HasAddon(script.extendedinfo)'):
                cmds.append((_('Movie information')+' (extendedinfo)',
                             addon.scriptaction('script.extendedinfo', info='extendedinfo', id=tmdb)))
                cmds.append((_('Trailer')+' (extendedinfo)',
                             addon.scriptaction('script.extendedinfo', info='playtrailer', id=tmdb)))

            if is_watched:
                cmds.append((_('Mark as unwatched'), addon.pluginaction('movies.unwatched', imdb=imdb)))
            else:
                cmds.append((_('Mark as watched'), addon.pluginaction('movies.watched', imdb=imdb)))

            cmds.append((_('Clear sources cache'),
                         addon.pluginaction('sources.clearsourcescache', name=urllib.quote_plus(label), imdb=imdb)))

            item = ui.ListItem(label=label, iconImage=poster, thumbnailImage=poster)

            try:
                item.setArt({'poster': poster, 'banner': banner})
            except Exception:
                pass

            if fanart_enabled:
                item.setProperty('Fanart_Image', fanart)

            item.setInfo(type='Video', infoLabels=meta)
            item.setProperty('Video', 'true')
            item.addContextMenuItems(cmds, replaceItems=False)
            ui.addItem(url, item, isFolder=True, totalItems=len(items))
        except Exception:
            import traceback
            log.notice(traceback.format_exc())

    if len(items) and 'next_action' in items[0]:
        ui.endDirectory(content='movies', next_item=items[0], sort_methods=[17, 18, 23])
    else:
        ui.endDirectory(content='movies', sort_methods=[17, 18, 23])


def _add_directory(items, show_genre_as=False, is_person=False):
    if not items:
        items = []

    addon_fanart = ui.addon_fanart()

    for i in items:
        try:
            try:
                name = _(i['name'])
            except Exception:
                name = i['name']

            url = addon.itemaction(i['action'], url=urllib.quote_plus(i['url']))

            cmds = []
            if is_person and i.get('id') and addon.condition('System.HasAddon(script.extendedinfo)'):
                cmds.append((_('Person information')+' (extendedinfo)',
                             addon.scriptaction('script.extendedinfo', info='extendedactorinfo', id=i['id'])))

            thumb = ui.media(i['image'])
            item = ui.ListItem(label=name, iconImage=thumb, thumbnailImage=thumb)

            if show_genre_as:
                if show_genre_as in i:
                    item.setInfo(type='Video', infoLabels={'genre': i[show_genre_as]})
                    item.setProperty('Video', 'true')

            if 'poster' in i:
                poster = ui.media(i['poster'])
                item.setArt({'poster': poster, 'banner': poster})

            item.addContextMenuItems(cmds, replaceItems=False)
            if addon_fanart:
                item.setProperty('Fanart_Image', addon_fanart)
            ui.addItem(url, item, isFolder=True, totalItems=len(items))
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', i, repr(ex))

    content = 'movies' if show_genre_as else None
    if len(items) and 'next_action' in items[0]:
        ui.endDirectory(content=content, next_item=items[0])
    else:
        ui.endDirectory(content=content)
