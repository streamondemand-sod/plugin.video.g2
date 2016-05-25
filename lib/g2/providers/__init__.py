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

import g2

from g2.libraries import log
from g2.libraries import workers
from g2.libraries import platform
from g2 import resolvers
from .lib.fuzzywuzzy import fuzz


_SOURCE_CACHE_LIFETIME = 3600 # secs
_MIN_FUZZINESS_VALUE = 84


def info():
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
                i['content'] = content
        return nfo

    return g2.info(__name__, source_info)


def video_sources(ui_update, content, **kwargs):
    providers = {}
    for dummy_kind, package in g2.packages([__name__]):
        providers[package] = [p for p in info().itervalues() if p['package'] == package and content in p['content']]
    all_providers = sum([len(providers[p]) for p in providers])
    if not all_providers:
        return []

    sources = {}
    all_completed_providers = 0
    for package, ps in providers.iteritems():
        if not ps: continue

        modules = sorted(set([p['module'] for p in ps]))
        with g2.Context(__name__, package, modules, ps[0]['search_paths']) as ms:
            if not ms: continue
            threads = []
            channel = []
            for m, module in zip(ms, modules):
                sub_modules = [p['name'] for p in ps if p['module'] == module]
                threads.extend([workers.Thread(_sources_worker, channel, m, s, content, **kwargs) for s in sub_modules])

            # TODO[opt]: start a maximum of # concurrent threads
            [t.start() for t in threads]

            completed_threads = []
            while len(completed_threads) < len(threads):
                completed_threads = sorted([t for t in threads if not t.is_alive()], key=lambda t: t.elapsed)
                # completed_threads = [t for t in threads if not t.is_alive()]
                new_sources = []
                for t in completed_threads:
                    if t.result is not None:
                        for s in t.result:
                            if s['url'] not in sources:
                                new_sources.append(s)
                                sources[s['url']] = s
                        all_completed_providers += 1
                        t.result = None
                if not ui_update:
                    time.sleep(1)
                    continue
                try:
                    if not ui_update(all_completed_providers, all_providers, new_sources):
                        # Inform all threads to abort ASAP
                        channel.append('abort')
                        break
                except Exception as e:
                    log.notice('video_sources(%s): %s'%(content, e))

    return sources.values()


def _sources_worker(channel, m, provider, content, **kwargs):
    key_video = '/'.join([kwargs.get(k) or '-' for k in ['imdb', 'season', 'episode']])

    log.notice('sources_worker(%s, %s, title=%s, year=%s): key_video=%s'%(provider, content, kwargs.get('title'), kwargs.get('year'), key_video))

    video_ref = None
    if key_video == '-/-/-':
        dbcon = None
    else:
        try:
            platform.makeDir(platform.dataPath)
            dbcon = database.connect(platform.sourcescacheFile, timeout=10)
            dbcon.row_factory = database.Row
            dbcon.execute("CREATE TABLE IF NOT EXISTS rel_url (provider TEXT, key_video TEXT, video_ref TEXT, UNIQUE(provider, key_video));")
            dbcon.execute("CREATE TABLE IF NOT EXISTS rel_src (provider TEXT, key_video TEXT, sources TEXT, timestamp TEXT, UNIQUE(provider, key_video));")
            dbcon.commit()
        except:
            pass

        try:
            # Check if the sources are already cached and still valid
            dbcur = dbcon.execute("SELECT * FROM rel_src WHERE provider = '%s' AND key_video = '%s'"%(provider, key_video))
            sqlrow = dbcur.fetchone()

            sql_ts = int(str(sqlrow['timestamp']).translate(None, '- :'))
            now_ts = int(datetime.datetime.now().strftime("%Y%m%d%H%M"))
            if now_ts - sql_ts < _SOURCE_CACHE_LIFETIME:
                sources = json.loads(sqlrow['sources'])
                log.notice('sources_worker(%s, ...): %d sources found in the cache'%(provider, len(sources)))
                return sources
        except:
            pass

        try:
            # Check if the video url is already cached (TOREVIEW: no expiration?)
            dbcur = dbcon.execute("SELECT * FROM rel_url WHERE provider = '%s' AND key_video = '%s'" % (provider, key_video))
            sqlrow = dbcur.fetchone()
            video_ref = json.loads(sqlrow['video_ref'])
        except:
            pass

    if not video_ref:
        get_function_name = 'get_movie' if content == 'movie' else 'get_episode'
        if 'abort' in channel:
            log.notice('sources_worker(%s): aborted at %s'%(provider, get_function_name))
            return []

        try:
            video_matches = getattr(m, get_function_name)(provider.split('.'), **kwargs)
        except Exception as e:
            # get functions might fail because of no title/episode found
            log.notice('%s.%s(...): %s'%(provider, get_function_name, e), trace=True)
            video_matches = None

        if not video_matches:
            log.notice('sources_worker(%s): no matches found'%provider)
        else:
            # TODO[episode]: review
            def cleantitle(title):
                if title:
                    title = re.sub(r'\(.*\)', '', title) # Anything within ()
                    title = re.sub(r'\[.*\]', '', title) # Anything within []
                return title

            title = kwargs['title']
            video_best_match = max(video_matches, key=lambda m: fuzz.token_sort_ratio(cleantitle(m[1]), title))
            confidence = fuzz.token_sort_ratio(cleantitle(video_best_match[1]), title)
            # (fixme) [user]: add setting for fuzziness min value and also allow to change it via context menu
            if confidence >= _MIN_FUZZINESS_VALUE: video_ref = video_best_match
            log.notice('sources_worker(%s): %d matches found; best has confidence %d (%s)'%(provider, len(video_matches), confidence, video_best_match[1]))

        if video_ref and dbcon:
            try:
                with dbcon:
                    dbcon.execute("DELETE FROM rel_url WHERE provider = '%s' AND key_video = '%s'" % (provider, key_video))
                    dbcon.execute("INSERT INTO rel_url Values (?, ?, ?)", (provider, key_video, json.dumps(video_ref)))
            except Exception as e:
                log.notice('sources_worker(%s): %s'%(provider, e))

    if 'abort' in channel:
        log.notice('sources_worker(%s): aborted at get_sources'%(provider))
        return []

    sources = []
    if video_ref:
        log.notice('sources_worker(%s).video_ref(%s)'%(provider, video_ref))
        try:
            sources = m.get_sources(provider.split('.'), video_ref)
        except:
            # get functions might fail because of no sources found
            pass
        if not sources: sources = []

    for s in sources:
        s.update({
            'provider': provider,
        })

    if dbcon:
        try:
            # Cache the sources (also in the fail scenario)
            with dbcon:
                dbcon.execute("DELETE FROM rel_src WHERE provider = '%s' AND key_video = '%s'" % (provider, key_video))
                dbcon.execute("INSERT INTO rel_src Values (?, ?, ?, ?)", (provider, key_video, json.dumps(sources), datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
        except Exception as e:
            log.error('sources_worker(%s): %s'%(provider, e))

    log.notice('sources_worker(%s): %d sources found'%(provider, len(sources)))

    return sources


_log_debug = True
def clear_sources_cache(**kwargs):
    try:
        key_video = '/'.join([kwargs.get(k) or '-' for k in ['imdb', 'season', 'episode']])
        log.debug('{m}.{f}(...): key_video=%s'%(key_video))
        platform.makeDir(platform.dataPath)
        dbcon = database.connect(platform.sourcescacheFile, timeout=10)
        with dbcon:
            dbcon.execute("DELETE FROM rel_src WHERE key_video = '%s'" % key_video)
    except Exception as e:
        log.error('{m}.{f}(...): %s'%(e))


# TODO[code]: get_movie -> movie
def get_movie(provider, **kwargs):
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with g2.Context(__name__, provider['package'], [provider['module']], provider['search_paths']) as m:
        return m[0].get_movie(provider['name'].split('.'), **kwargs)


# TODO[code]: get_sources -> sources
def get_sources(provider, url):
    if not url: return []
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    with g2.Context(__name__, provider['package'], [provider['module']], provider['search_paths']) as m:
        sources = m[0].get_sources(provider['name'].split('.'), url)
        for s in sources:
            s.update({
                'provider': provider['name'],
            })
        return sources


def resolve(provider, url):
    if not url: return None
    try:
        provider = info()[provider]
    except:
        raise Exception('Provider %s not available'%provider)

    # First try the resolution with the resolvers
    rurl = resolvers.resolve(url)

    # If the resolvers have sucessfully resolved the url, then bypass the source resolver
    if isinstance(rurl, basestring): return rurl

    # If the resolvers return any error other than the 'No resolver for', then stop the resolution
    if 'No resolver for' not in str(rurl): return rurl

    # Otherwise, try with the source resolver and then give the url back to the resolvers again
    try:
        with g2.Context(__name__, provider['package'], [provider['module']], provider['search_paths']) as m:
            # TODO[debug]: if successfull, enrich the resolvedurl with the source resolver too!
            url = m[0].resolve(provider['name'].split('.'), url)
    except Exception:
        # On any failure of the source resolver, return the error of the first resolvers invocation
        return rurl

    # Abort if the source resolver return a None or an error class, otherwise give a try again to the resolvers
    return resolvers.resolve(url) if isinstance(url, basestring) else url
