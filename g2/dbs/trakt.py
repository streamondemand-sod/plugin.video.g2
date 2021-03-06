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
import json
import time
import urllib
import urlparse

from g2.libraries import log
from g2.libraries import cache
from g2.libraries import client
from g2.libraries import addon
from g2.libraries.language import _

from g2 import defs

from . import normalize_imdb


info = {
    'domains': ['api-v2launch.trakt.tv'],
    'methods': ['resolve', 'movies', 'tvshows', 'lists', 'watched'],
}

_INFO_LANG = addon.language('infoLang')
_TRAKT_USER = addon.setting('trakt_user')

_COMMON_POST_VARS = {
    'client_id': defs.TRAKT_CLIENT_ID,
    'client_secret': '9899db3e81158f6ebbb7b5afbce043b99caa13fba98c527c00c44ca44eca72c5',
    'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
}

_COMMON_HEADERS = {
    'Content-Type': 'application/json',
    'trakt-api-key': defs.TRAKT_CLIENT_ID,
    'trakt-api-version': '2',
}

_BASE_URL = 'https://api-v2launch.trakt.tv'
_URLS = {
    # Public query
    'movies_trending{}': '/movies/trending?limit=20|168',
    'tvshows_trending{}': '/shows/trending?limit=20|168',

    # 'tvshows{title}': '/search?type=show&query={title}&limit=20', # -- tv shows query is implemented using tvdb

    # For the below urls trakt must be enabled and with a valid user id
    'lists{trakt_user_id}': '/users/{trakt_user_id}/lists -- {trakt_enabled}',
    'movies{trakt_user_id}{trakt_list_id}': '/users/{trakt_user_id}/lists/{trakt_list_id}/items -- {trakt_enabled}',
    'movies_collection{trakt_user_id}': '/users/{trakt_user_id}/collection/movies -- {trakt_enabled}',
    'movies_watchlist{trakt_user_id}': '/users/{trakt_user_id}/watchlist/movies -- {trakt_enabled}',
    'movies_ratings{trakt_user_id}': '/users/{trakt_user_id}/ratings/movies -- {trakt_enabled}',

    # For the below urls trakt must be enabled and with a valid token
    'movies_recommendations{}': ('/recommendations/movies?limit=%d -- {trakt_enabled}{trakt_token}'%
                                 defs.TRAKT_MAX_RECOMMENDATIONS),
    'watched.movie{imdb_id}': 'movie.imdb.{imdb_id} -- {trakt_enabled}{trakt_token}',
    'watched.episode{imdb_id}{season}{episode}': 'show.imdb.{imdb_id}.{season}.{episode} -- {trakt_enabled}{trakt_token}',
}


def resolve(kind=None, **kwargs):
    if not kind:
        return _URLS.keys()
    if kind not in _URLS:
        return None

    for key, val in {
            'trakt_enabled': False if addon.setting('trakt_enabled') == 'false' else True,
            'trakt_token': addon.setting('trakt.token'),
            'info_lang': _INFO_LANG,
        }.iteritems():
        if key not in kwargs and val:
            kwargs[key] = val

    for key, val in kwargs.iteritems():
        kwargs[key] = urllib.quote_plus(str(val))

    try:
        url = _URLS[kind].format(**kwargs).split(' ')[0]
        return url if not url.startswith('/') else _BASE_URL+url
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', kind, repr(ex))
        return None


def movies(url):
    return _content(url, 'movie')


def tvshows(url):
    return _content(url, 'show')


def _content(url, content='movie'):
    if '|' not in url:
        timeout = 0
    else:
        url, timeout = url.split('|')[0:2]
    query = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
    query.update({'extended': 'full,images'})
    query = (urllib.urlencode(query)).replace('%2C', ',')
    query_url = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + query

    res = _traktreq(query_url)

    max_pages = 0
    try:
        page = int(res.headers['X-Pagination-Page'])
        max_pages = int(res.headers['X-Pagination-Page-Count'])
        if max_pages and page >= max_pages:
            raise Exception('last page reached')

        page += 1
        query = dict(urlparse.parse_qsl(urlparse.urlsplit(url).query))
        query.update({'page': page})
        query = (urllib.urlencode(query)).replace('%2C', ',')
        next_url = url.replace('?' + urlparse.urlparse(url).query, '') + '?' + query + ('' if not timeout else '|'+timeout)
        next_url = next_url.encode('utf-8')
        next_page = page
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', query_url.replace(_BASE_URL, ''), repr(ex))
        next_url = ''
        next_page = 0

    log.debug('{m}.{f}: %s: next_url=%s, next_page=%s, max_pages=%s',
              query_url.replace(_BASE_URL, ''), next_url.replace(_BASE_URL, ''), next_page, max_pages)

    res = res.json()
    results = []
    for i in res:
        if content in i:
            item = i[content]
            # NOTE: if you have rated this content, report your rating instead of the community rating
            if 'rating' in i:
                item['rating'] = i['rating']
            results.append(item)
    if not results:
        results = res

    log.debug('{m}.{f}: %s: %d %ss', query_url.replace(_BASE_URL, ''), len(results), content)

    items = []
    for item in results:
        try:
            title = item['title']
            title = client.replaceHTMLCodes(title)
            title = title.encode('utf-8')

            year = item['year']
            year = re.sub('[^0-9]', '', str(year))
            year = year.encode('utf-8')

            imdb = item['ids'].get('imdb')
            imdb = normalize_imdb(imdb)

            tmdb = item['ids'].get('tmdb')
            if tmdb == None or tmdb == '':
                tmdb = '0'
            tmdb = re.sub('[^0-9]', '', str(tmdb))
            tmdb = tmdb.encode('utf-8')

            tvdb = item['ids'].get('tvdb')
            if tvdb == None or tvdb == '':
                tvdb = '0'
            tvdb = re.sub('[^0-9]', '', str(tvdb))
            tvdb = tvdb.encode('utf-8')

            tvrage = item['ids'].get('tvrage')
            if tvrage == None or tvrage == '':
                tvrage = '0'
            tvrage = re.sub('[^0-9]', '', str(tvrage))
            tvrage = tvrage.encode('utf-8')

            poster = '0'
            try: poster = item['images']['poster']['medium']
            except: pass
            if poster == None or not '/posters/' in poster: poster = '0'
            poster = poster.rsplit('?', 1)[0]
            poster = poster.encode('utf-8')

            banner = poster
            try: banner = item['images']['banner']['full']
            except: pass
            if banner == None or not '/banners/' in banner: banner = '0'
            banner = banner.rsplit('?', 1)[0]
            banner = banner.encode('utf-8')

            fanart = '0'
            try: fanart = item['images']['fanart']['full']
            except: pass
            if fanart == None or not '/fanarts/' in fanart: fanart = '0'
            fanart = fanart.rsplit('?', 1)[0]
            fanart = fanart.encode('utf-8')

            premiered = item.get('released')
            try: premiered = re.compile('(\d{4}-\d{2}-\d{2})').findall(premiered)[0]
            except: premiered = '0'
            premiered = premiered.encode('utf-8')

            genre = item.get('genres', [])
            genre = [i.title() for i in genre]
            if genre == []:
                genre = '0'
            genre = ' / '.join(genre)
            genre = genre.encode('utf-8')

            try: duration = str(item['runtime'])
            except: duration = '0'
            if duration == None: duration = '0'
            duration = duration.encode('utf-8')

            try: rating = str(item['rating'])
            except: rating = '0'
            if rating == None or rating == '0.0': rating = '0'
            rating = rating.encode('utf-8')

            try: votes = str(item['votes'])
            except: votes = '0'
            try: votes = str(format(int(votes),',d'))
            except: pass
            if votes == None: votes = '0'
            votes = votes.encode('utf-8')

            mpaa = item.get('certification')
            if mpaa == None:
                mpaa = '0'
            mpaa = mpaa.encode('utf-8')

            plot = item.get('overview')
            if plot == None:
                plot = '0'
            plot = client.replaceHTMLCodes(plot)
            plot = plot.encode('utf-8')

            try: tagline = item['tagline']
            except: tagline = None
            if tagline == None and not plot == '0': tagline = re.compile('[.!?][\s]{1,2}(?=[A-Z])').split(plot)[0]
            elif tagline == None: tagline = '0'
            tagline = client.replaceHTMLCodes(tagline)
            try: tagline = tagline.encode('utf-8')
            except: pass

            items.append({
                'title': title,
                'originaltitle': title,
                'year': year,
                'premiered': premiered,
                'studio': '0',
                'genre': genre,
                'duration': duration,
                'rating': rating,
                'votes': votes,
                'mpaa': mpaa,
                'director': '0',
                'writer': '0',
                'cast': '0',
                'plot': plot,
                'tagline': tagline,
                'code': imdb,
                'imdb': imdb,
                'tmdb': tmdb,
                'tvdb': tvdb,
                'tvrage': tvrage,
                'poster': poster,
                'banner': banner,
                'fanart': fanart,
                'next_url': next_url,
                'next_page': next_page,
                'max_pages': max_pages,
            })
        except Exception as ex:
            log.debug('{m}.{f}: %s: %s', item, repr(ex))

    return items


def lists(url):
    url = url.split('|')[0]
    res = _traktreq(url)
    res = res.json()

    log.debug('{m}.{f}: %s: %s'%(url.replace(_BASE_URL, ''), res))

    items = []
    for item in res:
        try:
            name = item['name']
            name = client.replaceHTMLCodes(name)
            name = name.encode('utf-8')

            listid = item['ids']['slug']
            listid = listid.encode('utf-8')

            items.append({
                'name': name,
                'trakt_list_id': listid,
            })
        except Exception:
            pass

    return items


def watched(kind, seen=None, **kwargs):
    url = resolve(kind, **kwargs)
    if not url:
        return None

    content_idxs = url.split('.')
    if content_idxs[0] == 'movie':
        content, id_type, id_value = content_idxs
    elif content_idxs[0] == 'show':
        content, id_type, id_value, season, episode = content_idxs
    else:
        return None

    if seen is None:
        indicators = _sync(content, timeout=10)
        indicators = [i for i in indicators if content in i and str(i[content]['ids'][id_type]) == id_value]

        log.debug('{m}.{f}: %s: %s', content_idxs, indicators)

        if content == 'movie':
            status = True if len(indicators) else None
        elif content == 'show':
            seasons = [s for i in indicators if 'seasons' in i for s in i['seasons'] if str(s['number']) == season]
            episodes = [e for s in seasons if 'episodes' in s for e in s['episodes'] if str(e['number']) == episode]
            status = True if len(episodes) else None

        log.debug('{m}.{f}: %s: %s', content_idxs, status)

        return status
    else:
        post = {
            content+'s': [{
                'ids': {
                    id_type: id_value
                }
            }]
        }
        if content == 'show' and int(season):
            post[content+'s'][0].update({
                'seasons': [{
                    'number': int(season),
                }]
            })
            if int(episode):
                post[content+'s'][0]['seasons'][0].update({
                    'episodes': [{
                        'number': int(episode),
                    }]
                })

        log.debug('{m}.{f}: %s: %s', seen, post)

        res = _traktreq('/sync/history' if seen else '/sync/history/remove', post)
        if res.status_code in [client.codes.ok, client.codes.created, client.codes.no_content]:
            _sync(content)
        # Give a change to the other backends to store the flag too!
        return None


def _sync(content, timeout=0):
    def traktreq(url):
        return _traktreq(url).content

    try:
        if time.time() - _sync.cache_time[content] > timeout * 60:
            raise Exception('in memory cache expired')
        return _sync.cache_history[content]
    except AttributeError:
        _sync.cache_history = {}
        _sync.cache_time = {}
    except Exception as ex:
        log.debug('{m}.{f}: %s (timeout=%d): %s', content, timeout, repr(ex))

    content_history = cache.get(traktreq, timeout, '/users/%s/watched/%ss'%(_TRAKT_USER, content), table='rel_trakt')
    _sync.cache_history[content] = json.loads(content_history)
    _sync.cache_time[content] = time.time()

    return _sync.cache_history[content]


def authDevice(ui_update):
    try:
        phase = _('Code generation failed')
        addon.setSetting('trakt.token', '')
        addon.setSetting('trakt.refresh', '')

        with client.Session(headers=_COMMON_HEADERS) as session:
            res = session.post(urlparse.urljoin(_BASE_URL, '/oauth/device/code'), json=_COMMON_POST_VARS).json()

            code = res['user_code']
            url = res['verification_url']
            device_code = res['device_code']
            expires_in = res['expires_in']
            interval = res['interval']

            post = _COMMON_POST_VARS
            post.update({
                'code': str(device_code),
            })

            phase = _('Device authorization failed')
            start_time = time.time()
            next_check_at = start_time + interval
            while time.time()-start_time < expires_in:
                if not ui_update(code, url, time.time()-start_time, expires_in):
                    raise Exception('aborted: '+_('User aborted authorization'))
                if time.time() < next_check_at:
                    continue

                res = session.post(urlparse.urljoin(_BASE_URL, '/oauth/device/token'), json=post)
                next_check_at = time.time() + interval

                if res.status_code in [400, 429]:
                    pass

                elif res.status_code != client.codes.ok:
                    res.raise_for_status()

                else:
                    tokens = res.json()
                    addon.setSetting('trakt.token', str(tokens['access_token']))
                    addon.setSetting('trakt.refresh', str(tokens['refresh_token']))

                    authorization = {'Authorization': 'Bearer %s'%str(tokens['access_token'])}

                    res = session.get(urlparse.urljoin(_BASE_URL, '/users/me'),
                                      headers=authorization, raise_error=True).json()
                    return res['username']

        raise Exception('aborted: '+_('Auhorization code expired'))

    except Exception as ex:
        if str(ex).startswith('aborted: '):
            log.notice('{m}.{f}: %s', repr(ex))
            raise Exception(str(ex)[9:])
        else:
            log.error('{m}.{f}: %s', repr(ex))
            raise Exception(phase)


def _traktreq(url, post=None, **kwargs):
    with client.Session(headers=_COMMON_HEADERS, **kwargs) as session:
        token = addon.setting('trakt.token')
        refresh_token = addon.setting('trakt.refresh')

        if not _TRAKT_USER or not token:
            return session.request(url, json=post, raise_error=True)

        authorization = {'Authorization': 'Bearer %s'%token}

        url = urlparse.urljoin(_BASE_URL, url)
        res = session.request(url, json=post, headers=authorization)
        if res.status_code in [client.codes.ok, client.codes.created, client.codes.no_content]:
            return res

        if res.status_code not in [401, 405]:
            res.raise_for_status()

        # Token expired, refresh it
        oauth = urlparse.urljoin(_BASE_URL, '/oauth/token')
        opost = _COMMON_POST_VARS
        opost.update({
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        })

        res = session.post(oauth, json=opost, raise_error=True).json()

        token = str(res['access_token'])
        refresh = str(res['refresh_token'])

        addon.setSetting('trakt.token', token)
        addon.setSetting('trakt.refresh', refresh)

        authorization = {'Authorization': 'Bearer %s'%token}

        return session.request(url, json=post, headers=authorization, raise_error=True)
