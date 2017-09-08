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
import urlparse

from g2.libraries import log
from g2.libraries import client

from . import normalize_imdb


info = {
    'domains': ['www.imdb.com'],
    'methods': ['resolve', 'movies', 'tvshows', 'lists'],
}

# (fixme) defs or user setting?
_IMDB_PAGE_COUNT = 20

_BASE_URL = 'http://www.imdb.com'
_URLS = {
    'lists{imdb_user_id}': '/user/{imdb_user_id}/lists|168',
    'movies{imdb_user_id}{imdb_list_id}': ('/list/{imdb_list_id}/?view=detail&sort=user_rating:desc&'
                                           'title_type=feature,short,tv_movie,tv_special,video,documentary,game|168'),
    'movies_boxoffice{}': ('/search/title?title_type=feature,tv_movie&'
                           'sort=boxoffice_gross_us,desc&count=%d&page=1|168'%_IMDB_PAGE_COUNT),
    'movies_oscar{}': ('/search/title?title_type=feature,tv_movie&groups=oscar_best_picture_winners&'
                       'sort=year,desc&count=%d&page=1|720'%_IMDB_PAGE_COUNT),
    'tvshows_popular{}': ('/search/title?title_type=tv_series,mini_series&num_votes=100,&release_date=,date[0]&'
                          'sort=moviemeter,asc&count=%d&page=1|720'%_IMDB_PAGE_COUNT),
}


def resolve(kind=None, **kwargs):
    if not kind:
        return _URLS.keys()
    if kind not in _URLS:
        return None

    for key, val in kwargs.iteritems():
        kwargs[key] = urllib.quote_plus(str(val))

    return _BASE_URL+_URLS[kind].format(**kwargs)


def movies(url):
    return _content(url, 'movies')


def tvshows(url):
    return _content(url, 'tvshows')


def _content(url, content):
    if '|' not in url:
        timeout = 0
    else:
        url, timeout = url.split('|')[0:2]

    result = client.get(url).content.decode('iso-8859-1')
    results = client.parseDOM(result, 'div', attrs={'class': 'lister-item.+?'})

    next_url, next_page, max_pages = _imdb_next_page(url, timeout, result)

    log.debug('{m}.{f}: %s: %d %s, next_url=%s, next_page=%s, max_pages=%s',
              url.replace(_BASE_URL, ''), len(results), content, next_url.replace(_BASE_URL, ''), next_page, max_pages)

    items = []
    for item in results:
        try:
            # <img alt="Il trono di spade" class="loadlate" data-tconst="tt0944947"
            #   height="98" src="http://ia.media-imdb.com/images/M/[...].jpg" width="67">
            try:
                title = client.parseDOM(item, 'img', ret='alt')[0]
            except Exception:
                title = ''
            title = title.encode('utf-8')

            try:
                imdb = client.parseDOM(item, 'img', ret='data-tconst')[0]
            except Exception:
                imdb = '0'
            imdb = normalize_imdb(imdb)

            poster = '0'
            try:
                poster = client.parseDOM(item, 'img', ret='src')[0]
            except Exception:
                pass
            try:
                poster = client.parseDOM(item, 'img', ret='loadlate')[0]
            except Exception:
                pass
            poster = re.sub(r'_(SX|SY|UX|UY)[\d_,A-Za-z]*', r'_\g<1>500', poster)
            poster = poster.encode('utf-8')

            # <span class="lister-item-year text-muted unbold">(I) (2015)</span>
            # <span class="lister-item-year text-muted unbold">(2011- )</span>
            year = client.parseDOM(item, 'span', attrs={'class': 'lister-item-year.*?'})[0]
            year = re.compile(r'\((\d{4}).*?\)').findall(year)[-1]
            year = year.encode('utf-8')

            # <span class="certificate">T</span>
            try:
                mpaa = client.parseDOM(item, 'span', attrs={'class': 'certificate'})[0]
            except Exception:
                mpaa = ''
            if not mpaa or mpaa == 'NOT_RATED':
                mpaa = '0'
            mpaa = mpaa.replace('_', '-')
            mpaa = client.replaceHTMLCodes(mpaa)
            mpaa = mpaa.encode('utf-8')

            # <span class="runtime">56 min</span>
            try:
                duration = client.parseDOM(item, 'span', attrs={'class': 'runtime'})[0]
                duration = re.compile(r'(\d+) min').findall(duration)[0]
            except Exception:
                duration = ''
            if not duration:
                duration = '0'
            duration = duration.encode('utf-8')

            # <span class="genre">Biography, Crime, Drama</span>
            try:
                genre = client.parseDOM(item, 'span', attrs={'class': 'genre'})[0]
            except Exception:
                genre = ''
            genre = [client.replaceHTMLCodes(g).strip() for g in genre.split(',')]
            genre = ' / '.join(genre)
            if not genre:
                genre = '0'
            genre = genre.encode('utf-8')

            # <div class="inline-block ratings-imdb-rating" name="ir" data-value="9,2">
            try:
                rating = client.parseDOM(item, 'div', attrs={'name': 'ir'}, ret='data-value')[0]
            except Exception:
                rating = ''
            if not rating:
                rating = '0'
            rating = rating.encode('utf-8')

            # <span name="nv" data-value="37873">37,873</span>
            try:
                votes = client.parseDOM(item, 'span', attrs={'name': 'nv'}, ret='data-value')[0]
            except Exception:
                votes = ''
            if not votes:
                votes = '0'
            votes = votes.encode('utf-8')

            items.append({
                'title': title,
                'originaltitle': title,
                'year': year,
                'premiered': '0',
                'studio': '0',
                'genre': genre,
                'duration': duration,
                'rating': rating,
                'votes': votes,
                'mpaa': mpaa,
                'director': '0',
                'writer': '0',
                'cast': '0',
                'plot': '0',
                'tagline': '0',
                'code': imdb,
                'imdb': imdb,
                'tmdb': '0',
                'tvdb': '0',
                'tvrage': '0',
                'poster': poster,
                'banner': '0',
                'fanart': '0',
                'next_url': next_url,
                'next_page': next_page,
                'max_pages': max_pages,
            })
            log.debug('{m}.{f}: %s', items[-1])

        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items


def _imdb_next_page(url, timeout, result):
    max_pages = 0
    try:
        next_url = client.parseDOM(result, 'div', attrs={'class': 'nav'})
        try:
            if next_url:
                max_items = int(str(re.search(r'of ([\d\.,]+)', next_url[0]).group(1)).translate(None, '.,'))
                max_pages, rem = divmod(max_items, _IMDB_PAGE_COUNT)
                max_pages += rem > 0
            else:
                next_url = client.parseDOM(result, 'div', attrs={'class': 'pagination'})
                max_pages = int(str(re.search(r'of ([\d\.,]+)', next_url[0]).group(1)).translate(None, '.,'))
        except Exception:
            max_pages = 0

        next_url = client.parseDOM(next_url[0], 'a', ret='href')[-1]
        next_url = url.replace(urlparse.urlparse(url).query, urlparse.urlparse(next_url).query)
        next_url = client.replaceHTMLCodes(next_url) + ('' if not timeout else '|'+timeout)
        next_url = next_url.encode('utf-8')

        curr_page = int(re.search(r'[&?]page=(\d+)', url).group(1))
        next_page = int(re.search(r'[&?]page=(\d+)', next_url).group(1))
        if next_page <= curr_page:
            raise Exception('last page reached')

    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', url.replace(_BASE_URL, ''), repr(ex))
        next_url = ''
        next_page = 0

    return next_url, next_page, max_pages


def lists(url):
    url = url.split('|')[0]
    result = client.get(url).content
    result = result.decode('iso-8859-1').encode('utf-8')
    results = client.parseDOM(result, 'div', attrs={'class': 'list-preview .*?'})

    log.debug('{m}.{f}: %s: %d lists', url.replace(_BASE_URL, ''), len(results))

    items = []
    for item in results:
        try:
            name = client.parseDOM(item, 'div', attrs={'class': 'list_name'})[0]
            name = client.parseDOM(name, 'a')[0]
            name = client.replaceHTMLCodes(name)
            name = name.encode('utf-8')

            listid = client.parseDOM(item, 'a', ret='href')[0]
            listid = listid.split('/list/', 1)[-1].replace('/', '')

            meta = client.parseDOM(item, 'div', attrs={'class': 'list_meta'})[0]
            meta = client.replaceHTMLCodes(meta)
            meta = meta.encode('utf-8')

            image = client.parseDOM(item, 'div', attrs={'class': 'list-preview-item-wide'})[0]
            image = client.parseDOM(image, 'img', ret='src')
            if not image:
                image = client.parseDOM(image, 'img', ret='loadlate')

            items.append({
                'name': name,
                'imdb_list_id': listid,
                'genre': meta,
            })
            if image:
                items[-1].update({
                    'image': image[0],
                })
        except Exception as ex:
            log.error('{m}.{f}: %s: %s', item, repr(ex))

    return items


def nickname(imdb_user_id):
    result = client.get(_BASE_URL+'/user/'+imdb_user_id).content
    return client.parseDOM(result, 'h1')[0]
