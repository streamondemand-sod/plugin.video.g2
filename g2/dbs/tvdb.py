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


import re
import urllib
import zipfile
import StringIO

from g2.libraries import log
from g2.libraries import addon
from g2.libraries import client
from g2.libraries import workers

from g2 import defs

from . import fields_mapping_xml


info = {
    'domains': ['thetvdb.com'],
    'methods': ['resolve', 'tvshows', 'meta'],
}

_INFO_LANG = addon.language('infoLang')
_KODI_LANG = addon.language(None)

_TVDB_APIKEY = addon.setting('tvdb_apikey') or defs.TVDB_APIKEY
_TVDB_IMAGE = 'http://thetvdb.com/banners/'
_TVDB_POSTER = 'http://thetvdb.com/banners/_cache/'

_BASE_URL = 'http://thetvdb.com/api'
_URLS = {
    'tvshows{title}': '/GetSeries.php?seriesname={title}&language={info_lang}',
    'tvshow_meta{imdb_id}{lang}': '/GetSeriesByRemoteID.php?imdbid={imdb_id}',
    'tvshow_meta{tvdb_id}{lang}': '/@APIKEY@/series/{tvdb_id}/all/{lang}.zip',
    'tvshow_seasons_meta{tvdb_id}{lang}': '/@APIKEY@/series/{tvdb_id}/all/{lang}.zip',
    'tvshow_episodes_meta{tvdb_id}{lang}': '/@APIKEY@/series/{tvdb_id}/all/{lang}.zip',
}


def resolve(kind=None, **kwargs):
    if not kind:
        return _URLS.keys()
    if kind not in _URLS:
        return None

    for key, val in {
            'info_lang': _INFO_LANG,
            'kodi_lang': _KODI_LANG,
    }.iteritems():
        if key not in kwargs:
            kwargs[key] = val

    for key, val in kwargs.iteritems():
        kwargs[key] = urllib.quote_plus(str(val))

    return _BASE_URL+_URLS[kind].format(**kwargs)


_SERIE_MAPPINGS_XML_DESC = [
    {'name': 'title',
     'tag': 'SeriesName',
    },
    {'name': 'year',
     'tag': 'FirstAired',
     'map': lambda i, v: re.search(r'(\d{4})', v).group(1),
     'optional': True,
    },
    {'name': 'imdb',
     'tag': 'IMDB_ID',
     'default': '0',
    },
    {'name': 'tvdb',
     'tag': 'id',
     'default': '0',
    },
    {'name': 'tmdb',
     'default': '0',
    },
    {'name': 'plot',
     'tag': 'Overview',
     'optional': True,
    },
    {'name': 'studio',
     'tag': 'Network',
     'optional': True,
    },
    {'name': 'banner',
     'tag': 'banner',
     'optional': True,
     'default': '0',
     'map': lambda i, v: '0' if not v else _TVDB_IMAGE+v,
    },
    {'name': 'fanart',
     'tag': 'fanart',
     'optional': True,
     'default': '0',
     'map': lambda i, v: '0' if not v else _TVDB_IMAGE+v,
    },
    {'name': 'poster',
     'tag': 'poster',
     'optional': True,
     'default': '0',
     'map': lambda i, v: '0' if not v else _TVDB_IMAGE+v,
    },
    {'name': 'premiered',
     'tag': 'FirstAired',
     'optional': True,
     'default': '0',
    },
    {'name': 'genre',
     'tag': 'Genre',
     'optional': True,
     'default': '0',
     'map': lambda i, v: ' / '.join([x for x in v.split('|') if x]),
    },
    {'name': 'duration',
     'tag': 'Runtime',
     'optional': True,
     'default': '0',
    },
    {'name': 'rating',
     'tag': 'Rating',
     'optional': True,
     'default': '0',
    },
    {'name': 'votes',
     'tag': 'RatingCount',
     'optional': True,
     'default': '0',
    },
    {'name': 'mpaa',
     'tag': 'ContentRating',
     'optional': True,
     'default': '0',
    },
    {'name': 'cast',
     'tag': 'Actors',
     'optional': True,
     'default': [],
     'map': lambda i, v: [x.encode('utf-8') for x in v.split('|') if x],
    },
]

_EPISODE_MAPPINGS_XML_DESC = [
    {'name': 'tvdb_episode_id',
     'tag': 'id',
     'optional': True,
    },
    {'name': 'tvdb_season_id',
     'tag': 'seasonid',
     'optional': True,
    },
    {'name': 'title',
     'tag': 'EpisodeName',
     'optional': True,
    },
    {'name': 'premiered',
     'tag': 'FirstAired',
     'map': lambda i, v: '0' if not v or '-00' in v else v,
    },
    {'name': 'season',
     'tag': 'SeasonNumber',
     'map': lambda i, v: str(int(re.sub(r'[^0-9]', '', v))),
    },
    {'name': 'episode',
     'tag': 'EpisodeNumber',
     'map': lambda i, v: str(int(re.sub(r'[^0-9]', '', v))),
    },
    {'name': 'plot',
     'tag': 'Overview',
     'optional': True,
    },
    {'name': 'poster',
     'tag': 'filename',
     'optional': True,
     'map': lambda i, v: '0' if not v else _TVDB_IMAGE+v,
     'default': '0',
    },
    {'name': 'rating',
     'tag': 'Rating',
     'optional': True,
     'default': '0',
    },
    {'name': 'votes',
     'tag': 'RatingCount',
     'optional': True,
     'default': '0',
    },
    {'name': 'director',
     'tag': 'Director',
     'optional': True,
     'map': lambda i, v: ' / '.join([x for x in v.split('|') if x]),
     'default': '0',
    },
    {'name': 'writer',
     'tag': 'Writer',
     'optional': True,
     'map': lambda i, v: ' / '.join([x for x in v.split('|') if x]),
     'default': '0',
    },
]

_BANNER_MAPPINGS_XML_DESC = [
    {'name': 'language',
     'tag': 'Language',
    },
    {'name': 'type',
     'tag': 'BannerType',
    },
    {'name': 'season',
     'tag': 'Season',
     'optional': True,
    },
    {'name': 'path',
     'tag': 'BannerPath'},
]


def tvshows(url):
    url = url.split('|')[0]
    result = client.get(url).content

    results = client.parseDOM(result, 'Series')
    results = [s for s in results
               if client.parseDOM(s, 'language') == [_INFO_LANG] or client.parseDOM(s, 'Language') == [_INFO_LANG]]

    log.debug('{m}.{f}: %s: %d tvshows', url.replace(_BASE_URL, ''), len(results))

    items = []
    for i in results:
        try:
            item = fields_mapping_xml(i, _SERIE_MAPPINGS_XML_DESC)
            items.append(item)
        except Exception as ex:
            log.debug('{m}.{f}: %s: %s', i, repr(ex))

    return items


def meta(metas):
    for i in range(0, len(metas), defs.MAX_CONCURRENT_THREADS):
        threads = [workers.Thread(_meta_worker, metas[j]) for j in range(i, min(len(metas), i+defs.MAX_CONCURRENT_THREADS))]
        dummy = [t.start() for t in threads]
        dummy = [t.join() for t in threads]


def _meta_worker(met):
    content = met['content']
    if not met['item']:
        pass
    elif (content == 'tvshow' or
          (met['item']['seasons'] and content == 'tvshow_seasons') or
          (met['item']['episodes'] and content == 'tvshow_episodes')):
        met['url'] = None
        return

    url = met['url'].split('|')[0]
    lang = met['lang']

    if not url.endswith('.xml') and not url.endswith('.zip'):
        serie_xml = client.get(url.replace('@APIKEY@', _TVDB_APIKEY, 1)).content
        tvdb_ids = client.parseDOM(serie_xml, 'id')
        if not tvdb_ids:
            return
        url = resolve('%s_meta{tvdb_id}{lang}'%content, tvdb_id=tvdb_ids[0], lang=lang)
        if not url:
            return
        url = url.split('|')[0]

    log.debug('{m}.{f}: %s: lang=%s, content=%s', url.replace(_BASE_URL, ''), lang, content)

    meta_xml = client.get(url.replace('@APIKEY@', _TVDB_APIKEY, 1)).content
    banner_xml = None
    if url.endswith('.zip'):
        zipdata = zipfile.ZipFile(StringIO.StringIO(meta_xml))
        meta_xml = zipdata.read('%s.xml'%lang)
        banner_xml = zipdata.read('banners.xml')
        zipdata.close()

    results = client.parseDOM(meta_xml, 'Series')
    results = [s for s in results
               if client.parseDOM(s, 'Language') == [lang] or client.parseDOM(s, 'language') == [lang]]

    log.debug('{m}.{f}: %s: %d tvshows meta for %s lang', url.replace(_BASE_URL, ''), len(results), lang)

    if not results:
        return

    tvshow = fields_mapping_xml(results[0], _SERIE_MAPPINGS_XML_DESC)

    tvshow['seasons'] = []
    tvshow['episodes'] = []
    met['item'] = tvshow
    met['url'] = None

    if met['content'] == 'tvshow':
        return

    season_banners = {}
    for i in client.parseDOM(banner_xml, 'Banner'):
        banner = fields_mapping_xml(i, _BANNER_MAPPINGS_XML_DESC)
        # The banners per season are mostly present only in the 'en' language
        if banner['language'] == 'en' and banner['type'] == 'season':
            try:
                season_banners[banner['season']].append(banner)
            except Exception:
                season_banners[banner['season']] = [banner]

    log.debug('{m}.{f}: %s: %d banners (en)', url.replace(_BASE_URL, ''), len(season_banners.keys()))

    tvshow_poster = tvshow['poster'] if tvshow['poster'] != '0' else tvshow['fanart'].replace(_TVDB_IMAGE, _TVDB_POSTER)

    results = client.parseDOM(meta_xml, 'Episode')

    log.debug('{m}.{f}: %s: %d episodes', url.replace(_BASE_URL, ''), len(results))

    for i in results:
        episode = fields_mapping_xml(i, _EPISODE_MAPPINGS_XML_DESC)
        if episode['season'] == '0':
            continue

        episode['tvshowtitle'] = tvshow['title']

        if int(episode['episode']) == 1:
            try:
                season_poster = _TVDB_IMAGE + season_banners[episode['season']][0]['path']
            except Exception:
                season_poster = tvshow_poster

            season = {
                'title': tvshow['title'],
                'season': episode['season'],
                'premiered': episode['premiered'],
                'poster': season_poster,
                'fanart': tvshow['fanart'],
            }
            for dbid in ['tvdb', 'imdb', 'tmdb']:
                season[dbid] = met[dbid]

            met['item']['seasons'].append(season)

        if episode['poster'] == '0':
            episode['poster'] = season_poster

        for dbid in ['tvdb', 'imdb', 'tmdb']:
            episode[dbid] = met[dbid]

        met['item']['episodes'].append(episode)
