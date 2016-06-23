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


import re
import sys
import json
import time
import datetime
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import fs
from g2.libraries import log
from g2.libraries import workers

from g2 import pkg
from g2 import resolvers

from .lib.fuzzywuzzy import fuzz


_SOURCE_CACHE_LIFETIME = 3600 # secs
_MIN_FUZZINESS_VALUE = 84
_IGNORE_BODY_EXCEPTIONS = True


def info(force=False):
    def source_info(package, module, m, paths):
        content = set()
        if hasattr(m, 'get_movie'):
            content.add('movie')
        if hasattr(m, 'get_episode'):
            content.add('episode')
        if not hasattr(m, 'info'):
            nfo = {}
        elif callable(m.info):
            nfo = m.info(paths)
        else:
            nfo = m.info
        if type(nfo) != list:
            nfo = [nfo]
        for i in nfo:
            if 'content' not in i:
                i['content'] = list(content)
        return nfo

    return pkg.info(__name__, source_info, force)


def content_sources(content, ui_update=None, **kwargs):
    providers = {}
    for dummy_kind, package in pkg.packages([__name__]):
        providers[package] = [mi for mi in info().itervalues() if mi['package'] == package and content in mi['content']]
    all_providers = sum([len(providers[mi]) for mi in providers])
    if not all_providers:
        return []

    sources = {}
    all_completed_providers = 0
    for package, modulesinfo in providers.iteritems():
        if not modulesinfo:
            continue

        modules = sorted(set([mi['module'] for mi in modulesinfo]))
        with pkg.Context(__name__, package, modules, modulesinfo[0]['search_paths'], ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mods:
            if not mods:
                continue
            threads = []
            channel = []
            for mod, module in zip(mods, modules):
                sub_modules = [mi['name'] for mi in modulesinfo if mi['module'] == module]
                threads.extend([workers.Thread(_sources_worker, channel, mod, smodule, content, **kwargs)
                                for smodule in sub_modules])

            dummy = [t.start() for t in threads]

            completed_threads = []
            while len(completed_threads) < len(threads):
                completed_threads = sorted([t for t in threads if not t.is_alive()], key=lambda t: t.elapsed)
                # completed_threads = [t for t in threads if not t.is_alive()]
                new_sources = []
                for thd in completed_threads:
                    if thd.result is not None:
                        for src in thd.result:
                            if src['url'] not in sources:
                                new_sources.append(src)
                                sources[src['url']] = src
                        all_completed_providers += 1
                        thd.result = None
                if not ui_update:
                    time.sleep(1)
                    continue
                try:
                    if not ui_update(all_completed_providers, all_providers, new_sources):
                        # Inform all threads to abort ASAP
                        channel.append('abort')
                        break
                except Exception as ex:
                    log.notice('{m}.{f}(%s): %s', content, ex)

    return sources.values()


def _sources_worker(channel, m, provider, content, **kwargs):
    key_video = '/'.join([kwargs.get(k) or '-' for k in ['imdb', 'season', 'episode']])

    log.notice('{m}.{f}(%s, %s, title=%s, year=%s): key_video=%s',
               provider, content, kwargs.get('title'), kwargs.get('year'), key_video)

    video_ref = None
    if key_video == '-/-/-':
        dbcon = None
    else:
        try:
            fs.makeDir(fs.PROFILE_PATH)
            dbcon = database.connect(fs.CACHE_DB_FILENAME, timeout=10)
            dbcon.row_factory = database.Row
            dbcon.execute('CREATE TABLE IF NOT EXISTS rel_url'
                          ' (provider TEXT, key_video TEXT, video_ref TEXT, UNIQUE(provider, key_video))')
            dbcon.execute('CREATE TABLE IF NOT EXISTS rel_src'
                          ' (provider TEXT, key_video TEXT, sources TEXT, timestamp TEXT, UNIQUE(provider, key_video));')
            dbcon.commit()
        except Exception:
            pass

        try:
            # Check if the sources are already cached and still valid
            dbcur = dbcon.execute("SELECT * FROM rel_src WHERE provider = ? AND key_video = ?",
                                  (provider, key_video))
            sqlrow = dbcur.fetchone()

            sql_ts = int(str(sqlrow['timestamp']).translate(None, '- :'))
            now_ts = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            if now_ts - sql_ts < _SOURCE_CACHE_LIFETIME:
                sources = json.loads(sqlrow['sources'])
                log.notice('{m}.{f}(%s, ...): %d sources found in the cache', provider, len(sources))
                return sources
        except Exception:
            pass

        try:
            # Check if the video url is already cached (TOREVIEW: no expiration?)
            dbcur = dbcon.execute("SELECT * FROM rel_url WHERE provider = ? AND key_video = ?",
                                  (provider, key_video))
            sqlrow = dbcur.fetchone()
            video_ref = json.loads(sqlrow['video_ref'])
        except Exception:
            pass

    if not video_ref:
        get_function_name = 'get_movie' if content == 'movie' else 'get_episode'
        if 'abort' in channel:
            log.notice('{m}.{f}(%s): aborted at %s', provider, get_function_name)
            return []

        try:
            video_matches = getattr(m, get_function_name)(provider.split('.'), **kwargs)
        except Exception as ex:
            # get functions might fail because of no title/episode found
            log.notice('{m}.{f}.%s.%s(...): %s', provider, get_function_name, ex, trace=True)
            video_matches = None

        if not video_matches:
            log.notice('{m}.{f}(%s): no matches found', provider)
        else:
            def cleantitle(title):
                if title:
                    title = re.sub(r'\(.*\)', '', title) # Anything within ()
                    title = re.sub(r'\[.*\]', '', title) # Anything within []
                return title

            title = kwargs['title']
            video_best_match = max(video_matches, key=lambda m: fuzz.token_sort_ratio(cleantitle(m[1]), title))
            confidence = fuzz.token_sort_ratio(cleantitle(video_best_match[1]), title)
            if confidence >= _MIN_FUZZINESS_VALUE:
                video_ref = video_best_match
            log.notice('{m}.{f}(%s): %d matches found; best has confidence %d (%s)',
                       provider, len(video_matches), confidence, video_best_match[1])

        if video_ref and dbcon:
            try:
                with dbcon:
                    dbcon.execute("DELETE FROM rel_url WHERE provider = ? AND key_video = ?",
                                  (provider, key_video))
                    dbcon.execute("INSERT INTO rel_url Values (?, ?, ?)",
                                  (provider, key_video, json.dumps(video_ref)))
            except Exception as ex:
                log.notice('{m}.{f}(%s): %s', provider, ex)

    if 'abort' in channel:
        log.notice('{m}.{f}(%s): aborted at get_sources', provider)
        return []

    sources = []
    if video_ref:
        log.notice('{m}.{f}(%s).video_ref(%s)', provider, video_ref)
        try:
            sources = m.get_sources(provider.split('.'), video_ref)
        except Exception as ex:
            log.debug('{m}.{f}: %s(%s): %s', provider, video_ref, repr(ex))

        if not sources:
            sources = []

    for src in sources:
        src.update({
            'provider': provider,
        })

    if dbcon:
        try:
            # Cache the sources (also in the fail scenario)
            with dbcon:
                dbcon.execute("DELETE FROM rel_src WHERE provider = ? AND key_video = ?",
                              (provider, key_video))
                dbcon.execute("INSERT INTO rel_src Values (?, ?, ?, ?)",
                              (provider, key_video, json.dumps(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
        except Exception as ex:
            log.error('{m}.{f}(%s): %s', provider, ex)

    log.notice('{m}.{f}(%s): %d sources found', provider, len(sources))

    return sources


def clear_sources_cache(**kwargs):
    try:
        key_video = '/'.join([kwargs.get(k) or '-' for k in ['imdb', 'season', 'episode']])
        log.debug('{m}.{f}(...): key_video=%s', key_video)
        fs.makeDir(fs.PROFILE_PATH)
        dbcon = database.connect(fs.CACHE_DB_FILENAME, timeout=10)
        with dbcon:
            dbcon.execute("DELETE FROM rel_src WHERE key_video = ?", (key_video,))
            dbcon.execute("DELETE FROM rel_url WHERE key_video = ?", (key_video,))
        return key_video
    except Exception as ex:
        log.error('{m}.{f}(...): %s', ex)
        return None


def get_movie(provider, **kwargs):
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                     ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mod:
        return mod[0].get_movie(provider['name'].split('.'), **kwargs)


def get_sources(provider, url):
    if not url:
        return []
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                     ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mod:
        sources = mod[0].get_sources(provider['name'].split('.'), url)
        for src in sources:
            src.update({
                'provider': provider['name'],
            })
        return sources


def resolve(provider, url):
    if not url:
        return None
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    # First try the resolution with the resolvers
    rurl = resolvers.resolve(url)

    # If the resolvers have sucessfully resolved the url, then bypass the source resolver
    if isinstance(rurl, basestring):
        return rurl

    # If the resolvers return any error other than the 'No resolver for', then stop the resolution
    if 'No resolver for' not in str(rurl):
        return rurl

    # Otherwise, try with the source resolver and then give the url back to the resolvers again
    try:
        with pkg.Context(__name__, provider['package'], [provider['module']], provider['search_paths'],
                         ignore_exc=_IGNORE_BODY_EXCEPTIONS) as mod:
            url = mod[0].resolve(provider['name'].split('.'), url)
    except Exception:
        # On any failure of the source resolver, return the error of the first resolvers invocation
        return rurl

    # Abort if the source resolver return a None or an error class, otherwise give a try again to the resolvers
    return resolvers.resolve(url) if isinstance(url, basestring) else url
