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


import os
import sys
import json
import urllib

from g2.libraries import log
from g2.libraries import cache
from g2.libraries import platform
from g2.libraries.language import _
from g2 import dbs

from .lib import metacache
from .lib import ui


_sysaddon = sys.argv[0]
_systhread = int(sys.argv[1])

_info_lang = platform.setting('infoLang') or 'en'
_imdb_user = platform.setting('imdb_user').replace('ur', '')
_trakt_user = platform.setting('trakt_user') if platform.setting('trakt_enabled') else ''


def menu(**kwargs):
    if dbs.url('movies_recently_added{}'):
        db_provider = dbs.url('movies_recently_added{}', db_provider=True)
        ui.addDirectoryItem(_('Latest Movies')+' ['+db_provider.upper()+']',
                            'movies.movielist&url='+dbs.url('movies_recently_added{}', quote_plus=True),
                            'moviesAdded.jpg', 'DefaultRecentlyAddedMovies.png')
    ui.addDirectoryItem(_('Search by Title'), 'movies.searchbytitle', 'movieSearch.jpg', 'DefaultMovies.png')
    ui.addDirectoryItem(_('Search by Person'), 'movies.searchbyperson', 'moviePerson.jpg', 'DefaultMovies.png')
    ui.addDirectoryItem(_('Search by Year'), 'movies.searchbyyear', 'movieYears.jpg', 'DefaultMovies.png')
    ui.addDirectoryItem(_('Genres'), 'movies.genres', 'movieGenres.jpg', 'DefaultMovies.png')
    ui.addDirectoryItem(_('Certificates'), 'movies.certifications', 'movieCertificates.jpg', 'DefaultMovies.png')
    if dbs.url('movies_featured{}'):
        ui.addDirectoryItem(_('Featured'), 'movies.movielist&url='+dbs.url('movies_featured{}', quote_plus=True),
                            'movies.jpg', 'DefaultRecentlyAddedMovies.png')
    if dbs.url('movies_trending{}'):
        ui.addDirectoryItem(_('People Watching'), 'movies.movielist&url='+dbs.url('movies_trending{}', quote_plus=True),
                            'moviesTrending.jpg', 'DefaultRecentlyAddedMovies.png')
    if dbs.url('movies_popular{}'):
        ui.addDirectoryItem(_('Most Popular'), 'movies.movielist&url='+dbs.url('movies_popular{}', quote_plus=True),
                            'moviesPopular.jpg', 'DefaultMovies.png')
    if dbs.url('movies_toprated{}'):
        ui.addDirectoryItem(_('Most Voted'), 'movies.movielist&url='+dbs.url('movies_toprated{}', quote_plus=True),
                            'moviesViews.jpg', 'DefaultMovies.png')
    if dbs.url('movies_boxoffice{}'):
        ui.addDirectoryItem(_('Box Office'), 'movies.movielist&url='+dbs.url('movies_boxoffice{}', quote_plus=True),
                            'moviesBoxoffice.jpg', 'DefaultMovies.png')
    if dbs.url('movies_oscar{}'):
        ui.addDirectoryItem(_('Oscar Winners'), 'movies.movielist&url='+dbs.url('movies_oscar{}', quote_plus=True),
                            'moviesOscars.jpg', 'DefaultMovies.png')
    if dbs.url('movies_theaters{}'):
        ui.addDirectoryItem(_('In Theaters'), 'movies.movielist&url='+dbs.url('movies_theaters{}', quote_plus=True),
                            'moviesTheaters.jpg', 'DefaultRecentlyAddedMovies.png')
    ui.endDirectory()


def searchbytitle(action, **kwargs):
    query = ui.doQuery(_('Title'))
    if query:
        url = dbs.url('movies{title}', title=query)
        movielist(action, url)


def searchbyperson(action, **kwargs):
    query = ui.doQuery(_('Person'))
    if query:
        url = dbs.url('persons{name}', name=query)
        personlist(action, url)


def searchbyyear(action, **kwargs):
    query = ui.doQuery(_('Year'))
    if query:
        url = dbs.url('movies{year}', year=query)
        movielist(action, url)


def genres(action, **kwargs):
    items = cache.get(dbs.genres, 24)
    for i in items:
        i.update({
            'action': 'movies.movielist',
            'url': dbs.url('movies{genre_id}', genre_id=i['id']),
        })
    _add_directory(action, items)


def certifications(action, **kwargs):
    items = cache.get(dbs.certifications, 24)
    items = sorted(items, key=lambda c: c['order'])
    for i in items:
        i.update({
            'action': 'movies.movielist',
            'url': dbs.url('movies{certification}', certification=i['name']),
        })
    _add_directory(action, items)


def movielist(action, url, **kwargs):
    items = cache.get(dbs.movies, 24, url)
    if not items:
        ui.infoDialog(_('No results'))
        return
    for i in items:
        i['next_action'] = 'movies.movielist'
    _fetch_movie_info(items)
    _add_movie_directory(action, items)


def personlist(action, url, **kwargs):
    items = cache.get(dbs.persons, 24, url)
    if not items:
        ui.infoDialog(_('No results'))
        return
    for i in items:
        i.update({
            'action': 'movies.movielist',
            'url': dbs.url('movies{person_id}', person_id=i['id']),
            'next_action': 'movies.tmdbpersonlist',
        })
    _add_directory(action, items)


def widget(action, **kwargs):
    setting = platform.setting('movie_widget')

    if setting == '2':
        url = dbs.url('movies_featured{}')
    elif setting == '3':
        url = dbs.url('movies_trending{}')
    else:
        url = dbs.url('movies_recently_added{}')
    movielist(action, url)


def userlists(action, **kwargs):
    items = []
    if _trakt_user:
        trakt_items = cache.get(dbs.lists, 0, dbs.url('lists{trakt_user_id}', trakt_user_id=_trakt_user))
        for i in trakt_items:
            i.update({
                'action': 'movies.movielist',
                'url': dbs.url('movies{trakt_user_id}{trakt_list_id}',
                               trakt_user_id=_trakt_user, trakt_list_id=i['trakt_list_id']),
            })
        items.extend(trakt_items)

    if _imdb_user:
        imdb_items = cache.get(dbs.lists, 0, dbs.url('lists{imdb_user_id}', imdb_user_id=_imdb_user))
        for i in imdb_items:
            i.update({
                'action': 'movies.movielist',
                'url': dbs.url('movies{imdb_list_id}', imdb_list_id=i['imdb_list_id']),
            })
        items.extend(imdb_items)

    if not items:
        ui.infoDialog(_('No results'))
        return
    # (fixme)[code]: here content='movies' means show genre and poster,
    # need to change to a much clearer way, eg:
    #   show_genre_as='imdb_list_meta'
    _add_directory(action, items, content='movies')


def watched(action, imdb, **kwargs):
    dbs.watched('movie{imdb_id}', True, imdb_id=imdb)
    ui.refresh()


def unwatched(action, imdb, **kwargs):
    dbs.watched('movie{imdb_id}', False, imdb_id=imdb)
    ui.refresh()


def _fetch_movie_info(items):
    metas = metacache.fetch(items, _info_lang)
    if metas:
        dbs.metas(metas)

        # Update all item attributes except fanart and rating if present
        for meta, i in zip(metas, items):
            if meta['item']:
                i.update(dict((k, v) for k, v in meta['item'].iteritems()
                              if k not in ['fanart', 'rating'] or (k in ['fanart', 'rating'] and i.get(k, '0') == '0')))

        metacache.insert(metas)


def _add_movie_directory(action, items):
    if not items:
        return

    addonPoster = platform.addonPoster()
    addonBanner = platform.addonBanner()
    addonFanart = platform.addonFanart()
    settingFanart = platform.setting('fanart')

    for i in items:
        try:
            label = i['name']
            systitle = urllib.quote_plus(i['title'])
            imdb, tmdb, year = i['imdb'], i['tmdb'], i['year']

            poster, banner, fanart = i['poster'], i['banner'], i['fanart']
            if poster == '0':
                poster = addonPoster
            if banner == '0' and poster == '0':
                banner = addonBanner
            elif banner == '0':
                banner = poster

            meta = dict((k, v) for k, v in i.iteritems() if not v == '0')
            # if i['duration'] == '0':
            #     meta.update({
            #         'duration': '120',
            #     })
            try:
                meta.update({
                    'duration': str(int(meta['duration']) * 60),
                })
            except Exception:
                pass
            sysmeta = urllib.quote_plus(json.dumps(meta))

            url = '%s?action=sources.dialog&title=%s&year=%s&imdb=%s&tmdb=%s&meta=%s'%\
                  (_sysaddon, systitle, year, imdb, tmdb, sysmeta)

            is_watched = dbs.watched('movie{imdb_id}', imdb_id=imdb)
            if is_watched:
                meta.update({
                    'playcount': 1,
                    'overlay': 7
                })

            cmds = []
            # (fixme)[user]: define a setting for choosing the Info / Trailer action to use
            # - the string may have a number of placeholders to be used as id
            if platform.condition('System.HasAddon(script.extendedinfo)'):
                cmds.append((_('Movie information'), "RunScript(script.extendedinfo,info=extendedinfo,id=%s)"%tmdb))
                cmds.append((_('Trailer'), 'RunScript(script.extendedinfo,info=playtrailer,id=%s)'%tmdb))
            else:
                cmds.append((_('Movie information'), 'Action(Info)'))

            cmds.append((_('Play items as folder once'), 'RunPlugin(%s?action=sources.usefolderonce)' % (_sysaddon)))
            if is_watched:
                cmds.append((_('Mark as unwatched'), 'RunPlugin(%s?action=movies.unwatched&imdb=%s)' % (_sysaddon, imdb)))
            else:
                cmds.append((_('Mark as watched'), 'RunPlugin(%s?action=movies.watched&imdb=%s)' % (_sysaddon, imdb)))

            cmds.append((_('Clear sources cache'), 'RunPlugin(%s?action=sources.clearsourcescache&imdb=%s)' % (_sysaddon, imdb)))

            item = ui.ListItem(label=label, iconImage=poster, thumbnailImage=poster)

            try:
                item.setArt({'poster': poster, 'banner': banner})
            except Exception:
                pass

            if settingFanart == 'true' and not fanart == '0':
                item.setProperty('Fanart_Image', fanart)
            elif addonFanart:
                item.setProperty('Fanart_Image', addonFanart)

            item.setInfo(type='Video', infoLabels=meta)
            item.setProperty('Video', 'true')
            item.addContextMenuItems(cmds, replaceItems=False)
            ui.addItem(handle=_systhread, url=url, listitem=item, isFolder=True)
            # NOTE: The following del avoids the issue of the message:
            # CPythonInvoker(114, /home/giordano/.kodi/addons/plugin.video.g2/plugin.py): the python script \
            # "/home/giordano/.kodi/addons/plugin.video.g2/plugin.py" has left several classes in memory that \
            # we couldn't clean up. The classes include: N9XBMCAddon7xbmcgui8ListItemE
            del item
        except Exception:
            import traceback
            log.notice(traceback.format_exc())

    if len(items) and 'next_action' in items[0]:
        ui.endDirectory(content='movies',
                        next_action=items[0]['next_action'],
                        next_url=items[0]['next_url'],
                        next_page=items[0]['next_page'])
    else:
        ui.endDirectory(content='movies')


def _add_directory(action, items, content=None):
    if not items:
        return

    addonPoster = platform.addonPoster()
    addonFanart = platform.addonFanart()
    addonThumb = platform.addonThumb()
    artPath = platform.artPath()

    for i in items:
        try:
            try:
                name = _(i['name'])
            except Exception:
                name = i['name']

            if i['image'].startswith('http://'):
                thumb = i['image']
            elif artPath:
                thumb = os.path.join(artPath, i['image'])
            else:
                thumb = addonThumb

            url = '%s?action=%s' % (_sysaddon, i['action'])
            try:
                url += '&url=%s' % urllib.quote_plus(i['url'])
            except Exception:
                pass

            cmds = []
            item = ui.ListItem(label=name, iconImage=thumb, thumbnailImage=thumb)

            if content == 'movies':
                if 'genre' in i:
                    item.setInfo(type='Video', infoLabels={'genre': i['genre']})
                    item.setProperty('Video', 'true')
                if 'poster' in i:
                    if i['poster'].startswith('http://'):
                        poster = i['poster']
                    elif artPath:
                        poster = os.path.join(artPath, i['poster'])
                    else:
                        poster = addonPoster
                    item.setArt({'poster': poster, 'banner': poster})

            # (fixme) no context commands here, for example to get person details?!?
            item.addContextMenuItems(cmds, replaceItems=True)
            if addonFanart:
                item.setProperty('Fanart_Image', addonFanart)
            ui.addItem(handle=_systhread, url=url, listitem=item, isFolder=True)
        except Exception:
            pass

    if len(items) and 'next_action' in items[0]:
        ui.endDirectory(content=content,
                        next_action=items[0]['next_action'],
                        next_url=items[0]['next_url'],
                        next_page=items[0]['next_page'])
    else:
        ui.endDirectory(content=content)
