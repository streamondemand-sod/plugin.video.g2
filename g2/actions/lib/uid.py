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


_FANART = ui.addon_fanart()
_ICON_NEXT = ui.addon_next()


def additems(items, show_genre_as=False, is_person=False):
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
            ui.additem(url, item, isFolder=True, totalItems=len(items))
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', i, repr(ex))

    content = 'movies' if show_genre_as else None
    if len(items) and 'next_action' in items[0]:
        finish(content=content, next_item=items[0])
    else:
        finish(content=content)


def addcontentitems(items, content='movies'):
    if not items:
        items = []

    addon_poster = ui.addon_poster()
    addon_banner = ui.addon_banner()
    fanart_enabled = addon.setting('fanart') == 'true'

    for i in items:
        try:
            label = i['name']
            url = i['action']
            tmdb = i['tmdb']
            tvdb = i['tvdb']
            imdb = i['imdb']
            title = i['title']
            tvshowtitle = i.get('tvshowtitle')
            season = i.get('season', 0)
            episode = i.get('episode', 0)

            poster = i.get('poster', '0')
            if poster == '0':
                poster = addon_poster
            banner = i.get('banner', '0')
            if banner == '0':
                banner = addon_banner if poster == '0' else poster
            fanart = i.get('fanart', '0')
            if fanart == '0':
                fanart = _FANART

            meta = dict((k, v) for k, v in i.iteritems() if v and v != '0')
            try:
                meta['duration'] = str(int(meta['duration']) * 60)
            except Exception:
                pass

            cmds = []

            content_info_labels = {
                'movies': _('Movie information'),
                'tvshows': _('TV Show information'),
                'seasons': _('Season information'),
                'episodes': _('Episode information'),
            }
            content_info_label = content_info_labels.get(content)

            if content_info_label:
                cmds.append((content_info_label, 'Action(Info)'))

            # Create the script.extendedinfo commands
            if content_info_label and addon.condition('System.HasAddon(script.extendedinfo)'):
                # NOTE: for possible extendedinfo menu actions and the required parameters, see:
                # https://github.com/phil65/script.extendedinfo/blob/master/resources/lib/process.py
                content_extinfo_label = content_info_label+' (extendedinfo)'
                if content == 'movies':
                    if tmdb != '0':
                        cmds.append((content_extinfo_label,
                                     addon.scriptaction('script.extendedinfo', info='extendedinfo',
                                                        id=tmdb)))
                        cmds.append((_('Trailer')+' (extendedinfo)',
                                     addon.scriptaction('script.extendedinfo', info='playtrailer',
                                                        id=tmdb)))
                elif content == 'tvshows':
                    if tvdb != '0':
                        cmds.append((content_extinfo_label,
                                     addon.scriptaction('script.extendedinfo', info='extendedtvinfo',
                                                        tvdb_id=tvdb)))
                elif content == 'seasons':
                    if title and season:
                        cmds.append((content_extinfo_label,
                                     addon.scriptaction('script.extendedinfo', info='seasoninfo',
                                                        tvshow=title, season=season)))
                elif content == 'episodes':
                    if tvshowtitle and season and episode:
                        cmds.append((content_extinfo_label,
                                     addon.scriptaction('script.extendedinfo', info='extendedepisodeinfo',
                                                        tvshow=tvshowtitle, season=season, episode=episode)))

            # Check if the video has been aleady watched:
            # - Set the corresponding flag in the directory item
            # - create the watched/unwatched commands
            if imdb == '0':
                is_watched = None
            elif content == 'movies':
                is_watched = dbs.watched('movie{imdb_id}',
                                         imdb_id=imdb) is True
            elif content in ['tvshows', 'seasons', 'episodes']:
                is_watched = dbs.watched('episode{imdb_id}{season}{episode}',
                                         imdb_id=imdb, season=season, episode=episode) is True
            else:
                is_watched = None

            if is_watched:
                meta.update({
                    'playcount': 1,
                    'overlay': 7
                })

            if is_watched is not None:
                if is_watched:
                    watch_command_label = _('Mark as unwatched')
                    watch_command = 'unwatched'
                else:
                    watch_command_label = _('Mark as watched')
                    watch_command = 'watched'
                if content == 'movies':
                    cmds.append((watch_command_label, addon.pluginaction('movies.%s'%watch_command,
                                                                         imdb=imdb)))
                elif content in ['tvshows', 'seasons', 'episodes']:
                    cmds.append((watch_command_label, addon.pluginaction('tvshows.%s'%watch_command,
                                                                         imdb=imdb, season=season, episode=episode)))

            cmds.append((_('Clear sources cache'), addon.pluginaction('sources.clearsourcescache',
                                                                      name=urllib.quote_plus(label),
                                                                      imdb=imdb, season=season, episode=episode)))

            item = ui.ListItem(label=label, iconImage=poster, thumbnailImage=poster)

            try:
                item.setArt({
                    'poster': poster,
                    'banner': banner,
                })
                if content in ['tvshows', 'seasons', 'episodes']:
                    item.setArt({
                        'tvshow.poster': poster,
                        'season.poster': poster,
                        'tvshow.banner': banner,
                        'season.banner': banner,
                    })    
            except Exception:
                pass

            if fanart_enabled:
                item.setProperty('Fanart_Image', fanart)

            item.setInfo(type='Video', infoLabels=meta)
            item.setProperty('Video', 'true')
            item.addContextMenuItems(cmds, replaceItems=False)

            url = url.replace('@META@', urllib.quote_plus(json.dumps(meta)))
            ui.additem(url, item, isFolder=True, totalItems=len(items))
        except Exception as ex:
            log.debug('{m}.{f}: %s: %s', i, repr(ex))

    if len(items) and 'next_action' in items[0]:
        finish(content=content, next_item=items[0], sort_methods=[17, 18, 23])
    else:
        finish(content=content, sort_methods=[17, 18, 23])


def additem(name, query, thumb, icon, context=None, isAction=True, isFolder=True, totalItems=None):
    thumb = ui.media(thumb, icon)
    item = ui.ListItem(label=name, iconImage=thumb, thumbnailImage=thumb)

    cmds = []
    if context:
        cmds.append((context[0], context[1][1:] if context[1][0] == ':' else addon.pluginaction(context[1])))
    item.addContextMenuItems(cmds, replaceItems=False)

    if _FANART:
        item.setProperty('Fanart_Image', _FANART)

    url = addon.itemaction(query) if isAction else query

    ui.additem(url, item, isFolder=isFolder, totalItems=totalItems)


def finish(next_item=None, content=None, sort_methods=None):
    viewmode = None
    if type(next_item) == dict and next_item.get('next_action') and next_item.get('next_url'):
        log.debug('{m}.{f}: next_action:%s, next_url:%s, next_page:%s, max_pages:%s',
                  next_item.get('next_action'), next_item.get('next_url'), next_item.get('next_page'), next_item.get('max_pages'))

        url = addon.itemaction(next_item['next_action'], url=urllib.quote_plus(next_item['next_url']))

        if next_item.get('max_pages') and next_item.get('next_page'):
            # Label for the "Next Page" item when the max number of pages is known
            next_page_label = _('[I]Next Page[/I]  [{page_of} of {max_pages}]').format(
                page_of=next_item['next_page'],
                max_pages=next_item['max_pages']
            )
        elif next_item.get('next_page'):
            # Label for the "Next Page" item when only the current page number is known
            next_page_label = _('[I]Next Page[/I]  [{page_of}}]').format(
                page_of=next_item['next_page'],
            )
        else:
            next_page_label = _('[I]Next Page[/I]')

        item = ui.ListItem(label=next_page_label, iconImage=_ICON_NEXT, thumbnailImage=_ICON_NEXT)
        item.addContextMenuItems([], replaceItems=False)

        if _FANART:
            item.setProperty('Fanart_Image', _FANART)

        ui.additem(url, item, isFolder=True)

        # On paged directories, replicate the current viewmode when displaying the pages after the first
        if next_item.get('next_page') > 2:
            viewmode = ui.viewmode()

    else:
        # For non-paged directories, add the sorting methods, if provided
        ui.addsortmethods(sort_methods)

    ui.setcontent(content)

    ui.finish()

    if viewmode:
        ui.execute("Container.SetViewMode(%s)" % viewmode)
