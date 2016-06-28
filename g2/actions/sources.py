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


import json
import hashlib
import urlparse
try:
    from sqlite3 import dbapi2 as database
except:
    from pysqlite2 import dbapi2 as database

from g2.libraries import fs
from g2.libraries import log
from g2.libraries import workers
from g2.libraries import addon
from g2.libraries.language import _

from g2 import pkg
from g2 import dbs
from g2 import defs
from g2 import providers
from g2 import resolvers

from .lib import ui
from .lib import downloader
from . import action


@action
def playurl(name=None, url=None):
    try:
        if not url:
            return

        ui.busydialog()
        def ui_cancel():
            return not ui.abortRequested(1)
        thd = _resolve(None, url, ui_update=ui_cancel)
        ui.busydialog(stop=True)

        if not thd or thd.is_alive():
            return

        if not isinstance(thd.result, basestring):
            ui.infoDialog(_('Not a valid stream'))
            return

        url = thd.result
        ui.PlayerDialog().run(name, None, url)

    except Exception as ex:
        log.error('{m}.{f}: %s: %s', url, repr(ex))
        ui.infoDialog(_('Not a valid stream'))


@action
def clearsourcescache(name, **kwargs):
    if name and providers.clear_sources_cache(**kwargs):
        ui.infoDialog(_('Cache cleared for {video}').format(video=name))


@action
def dialog(title=None, year=None, imdb='0', tvdb='0', meta=None, **kwargs):
    try:
        meta = {} if not meta else json.loads(meta)

        if not ui.infoLabel('Container.FolderPath').startswith('plugin://'):
            ui.PlayList.clear()

        if ui.isfolderaction():
            ui.resolvedPlugin()
            ui.execute('Action(Back,10025)')

        imdb = 'tt%07d'%int(str(imdb).translate(None, 't'))
        name = '%s (%s)'%(title, year)
        content = 'movie'

        poster = meta.get('poster', '0')
        if poster == '0':
            poster = ui.addon_poster()

        log.debug('{m}.{f}: %s %s: meta:%s', name, imdb, meta)

        def sources_generator(self):
            def ui_update(progress, total, new_results):
                self.addItems(_sources_label(new_results))
                self.updateDialog(progress=(progress, total))
                if not self.userStopped():
                    ui.sleep(1000)
                return not self.userStopped()

            providers.content_sources(content, ui_update=ui_update,
                                      title=title, year=year, imdb=imdb, tvdb=tvdb, **kwargs)

        win = ui.SourcesDialog('SourcesDialog.xml', addon.PATH, 'Default', '720p',
                               sourceName=name,
                               sourcesGenerator=sources_generator,
                               sourcePriority=_source_priority,
                               sourceResolve=_resolve,
                               posterImage=poster)

        ui.idle()

        while True:
            win.doModal()

            item = win.selected
            if not item:
                break

            if win.action == 'play':
                if _play_source(name, imdb, tvdb, meta, item):
                    break

            elif win.action == 'download':
                _download_source(name, poster, item)

            win.show()

        del win

    except Exception as ex:
        log.error('{m}.{f}: %s', ex)
        ui.infoDialog(_('No stream available'))


def _play_source(name, imdb, dummy_tvdb, meta, item):
    url = item.getProperty('url')

    try:
        offset = _get_bookmark(name, imdb)
        if offset:
            minutes, seconds = divmod(int(offset), 60)
            hours, minutes = divmod(minutes, 60)
            if not ui.yesnoDialog(
                    heading=_('Resume from {hours:02d}:{minutes:02d}:{seconds:02d}').format(
                        hours=hours, minutes=minutes, seconds=seconds),
                    line1=name,
                    yeslabel=_('Resume'),
                    nolabel=_('Start from beginning')):
                offset = 0
        log.debug('{m}.{f}: %s %s: bookmark=%d', name, imdb, offset)
    except Exception as ex:
        offset = 0
        log.debug('{m}.{f}: %s %s: %s', name, imdb, repr(ex))

    credits_message = [
        m.format(
            video=name,
            provider=item.getProperty('source_provider').split('.')[-1],
            host=item.getProperty('source_host'),
            media_format=item.getProperty('format') or '???',
            elapsed_time='{elapsed_time}',
        ) for m in [
            _('~*~ CREDITS ~*~'),
            _('{video} loaded in {elapsed_time} seconds'),
            _('Source provided by [UPPERCASE][B]{provider}[/B][/UPPERCASE]'),
            _('Content hosted by [UPPERCASE][COLOR orange]{host}[/COLOR][/UPPERCASE]'),
            _('Media format is [UPPERCASE][COLOR FF009933]{media_format}[/COLOR][/UPPERCASE]'),
        ]]

    player = ui.PlayerDialog()
    player_status = player.run(name, meta, url, offset=offset, info=credits_message)

    _del_bookmark(name, imdb)
    if player_status < 0:
        log.notice('{m}.{f}: %s: %s: invalid source', name, url)
        source = item.getLabel()
        ui.infoDialog(_('Not a valid stream'), heading=source)
        ui.sleep(2000)
        item.setProperty('source_url', '')
        item.setProperty('url', '')

    elif player_status > defs.WATCHED_THRESHOLD:
        # (fixme) user setting to sync the watched status w/ each backend
        watched = dbs.watched('movie{imdb_id}', imdb_id=imdb)
        if not watched:
            watched = True
            dbs.watched('movie{imdb_id}', watched, imdb_id=imdb)
            ui.refresh()
        return True

    elif player_status > 2:
        _add_bookmark(player.elapsed(), name, imdb)

    return False


def _download_source(name, poster, item):
    url = item.getProperty('url')

    media_format = item.getProperty('type')
    try:
        media_size = int(item.getProperty('size'))
    except Exception:
        media_size = 0
    rest = item.getProperty('rest') == 'true'

    media_info1 = '' if not media_size else _('Complete file is {mega_bytes}MB {restartable_flag}').format(
        mega_bytes=int(media_size/(1024*1024)),
        # 'R' stand for Restartable download
        restartable_flag=_('(R)') if rest else '',
    )

    media_info2 = '' if not media_format else _('Media format is {media_format}').format(
        media_format=media_format
    )

    if ui.yesnoDialog(media_info1, media_info2, _('Continue with the download?')):
        if downloader.addDownload(name, url, media_format, media_size, rest, poster):
            ui.infoDialog(_('Item added to your download queue'), name)
        else:
            ui.infoDialog(_('Item already in your download queue'), name)


def _sources_label(sources):
    provider_index = -1
    provider_label = ''
    for i, source in enumerate(sources):
        provider = source['provider'].split('.')[-1].lower()
        if provider_index < 0 or provider != provider_label:
            provider_index = i
            provider_label = provider

        label = ''
        label += ('[B][I]%s [/I][/B]' if source['quality'] in ['1080p', 'HD'] else '[I]%s[/I]')%source['quality']
        label += ' | [B]%s #%s[/B] | %s'%(provider, i-provider_index+1, source['source'])

        source['label'] = label
    return sources


def _source_priority(host, provider, quality_tag=None, resolution=0):
    """Calculate the source priority based on:
    - Stream resolution if derived from the stream metadata
    - Source quality as indicated by the source provider
    - User preference for the source provider
    - User preference for the source host
    """
    # Actual resolution wins all over criteria
    priority = resolution * 1000

    # (fixme) [code]: define the labels as class constants in lib/sources/__init__.py:
    # class SourceQuality:
    #   res_8K = '8K',
    #   res_4K = '4K',
    # ...
    # so that sources/providers modules can use SourceQuality.res_8K as tag
    _quality_priority = {
        '8K': 400,
        '4K': 300,
        '1080p': 200,
        'HD': 100,
        'SD': 0,
    }

    # then use quality tags set by the providers
    priority += _quality_priority.get(quality_tag, 0)

    # then use the user preference for the source providers
    if provider:
        provider = provider.split('.')[-1].lower()
        for top in range(1, 10):
            pref = pkg.setting('providers', name='preferred_provider_%d'%top)
            if not pref:
                break
            if pref.lower() == provider:
                priority += 10 * (10 - top)

    # finally use the user preference for the content hosts
    if host:
        host = host.split('.')[-1].lower()
        for top in range(1, 10):
            pref = pkg.setting('resolvers', name='preferred_host_%d'%top)
            if not pref:
                break
            if  pref.lower() == host:
                priority += 10 - top

    return priority


def _resolve(provider, url, ui_update=None):
    if provider:
        thd = workers.Thread(providers.resolve, provider, url)
    else:
        thd = workers.Thread(resolvers.resolve, url)
    thd.start()

    keyboard_opened = False
    ui_cancelled = False
    for i in range(3600):
        key_open = ui.condition('Window.IsActive(virtualkeyboard)')
        if key_open:
            keyboard_opened = True
        if (i > defs.RESOLVER_TIMEOUT and not key_open) or not thd.is_alive():
            break
        if ui_update and not ui_update():
            ui_cancelled = True
            break
        ui.sleep(500)

    for i in range(defs.RESOLVER_TIMEOUT):
        if keyboard_opened or ui_cancelled or not thd.is_alive():
            break
        if ui_update and not ui_update():
            ui_cancelled = True
            break
        ui.sleep(500)

    extrainfo = ''
    if ui_cancelled:
        what = 'cancelled by the user after'
    elif thd.is_alive():
        what = 'timeout after'
    elif thd.exc:
        what = 'raised an exception after'
        extrainfo = ' ['+str(thd.exc)+']'
    elif not isinstance(thd.result, basestring):
        what = 'unsuccessfully completed in'
        extrainfo = ' []' if not thd.result else ' '+str(thd.result)
        thd.result = None
    else:
        what = 'successfully completed in'
        rurl = thd.result
        try:
            urlparsed = urlparse.urlparse(rurl)
            host = '%s://%s/.../%s'%(urlparsed.scheme, urlparsed.netloc, urlparsed.path.split('/')[-1])
        except Exception:
            host = rurl

        extrainfo = '%s"%s"'%('' if not hasattr(rurl, 'resolver') else ' by %s '%rurl.resolver, host)
        if hasattr(rurl, 'meta') and rurl.meta and 'firstbytes' in rurl.meta:
            import string
            extrainfo += ' [first %d bytes: %s]'%(
                len(rurl.meta['firstbytes']),
                ' '.join(['%02x%s'%(ord(b), ' (%s)'%b if b in string.printable else '') for b in rurl.meta['firstbytes']]))

    log.notice('{m}.{f}(%s, %s): %s %.3f secs%s'%(provider, url, what, thd.elapsed(), extrainfo))

    # (fixme): [obs] caching and stats
    # - cache successes and failures for 10mins
    # - keep a statistics of the failed host/domains: total call/success

    return None if ui_cancelled else thd


def _add_bookmark(bookmarktime, name, imdb):
    try:
        idfile = _bookmark_id(name, imdb)
        fs.makeDir(fs.PROFILE_PATH)
        dbcon = database.connect(fs.SETTINGS_DB_FILENAME)
        with dbcon:
            dbcon.execute("CREATE TABLE IF NOT EXISTS bookmark (idfile TEXT, bookmarktime INTEGER, UNIQUE(idfile))")
            dbcon.execute("DELETE FROM bookmark WHERE idfile = ?", (idfile,))
            dbcon.execute("INSERT INTO bookmark Values (?, ?)", (idfile, bookmarktime,))
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', name, repr(ex))


def _get_bookmark(name, imdb):
    try:
        idfile = _bookmark_id(name, imdb)
        dbcon = database.connect(fs.SETTINGS_DB_FILENAME)
        dbcon.row_factory = database.Row
        dbcur = dbcon.execute("SELECT * FROM bookmark WHERE idfile = ?", (idfile,))
        match = dbcur.fetchone()
        return match['bookmarktime'] if match else 0
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', name, repr(ex))
        return 0


def _del_bookmark(name, imdb):
    try:
        idfile = _bookmark_id(name, imdb)
        dbcon = database.connect(fs.SETTINGS_DB_FILENAME)
        dbcon.row_factory = database.Row
        with dbcon:
            dbcon.execute("DELETE FROM bookmark WHERE idfile = ?", (idfile,))
    except Exception as ex:
        log.debug('{m}.{f}: %s: %s', name, repr(ex))


def _bookmark_id(name, imdb):
    idfile = hashlib.md5()
    idfile.update(name)
    idfile.update(imdb)
    return str(idfile.hexdigest())
