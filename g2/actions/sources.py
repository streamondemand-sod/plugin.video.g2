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


import sys
import json
import time
import urllib
import urlparse

from g2 import pkg
from g2 import providers
from g2 import resolvers
from g2.libraries import log
from g2.libraries import workers
from g2.libraries import platform
from g2.libraries.language import _

from .lib import ui
from .lib import downloader
from . import action


_addon = sys.argv[0]
_thread = int(sys.argv[1])

_RESOLVER_TIMEOUT = 30 # seconds


@action
def playurl(title=None, url=None):
    try:
        if not url:
            return

        # (fixme) need to find a more portable way to identify a file steaming...
        if url.startswith('/'):
            pass
        else:
            ui.busydialog()
            def ui_cancel():
                ui.sleep(1000)
                return not ui.abortRequested()
            thd = _resolve(None, url, ui_update=ui_cancel)
            ui.busydialog(stop=True)

            if not thd or thd.is_alive():
                return

            if not isinstance(thd.result, basestring):
                ui.infoDialog(_('Not a valid stream'))
                return

            url = thd.result

        ui.Player().run(title, None, None, None, None, None, None, url)

    except Exception as ex:
        log.error('{m}.{f}: %s', ex)
        ui.infoDialog(_('Not a valid stream'))


@action
def dialog(title=None, year=None, imdb='0', tmdb='0', tvdb='0', meta=None, **kwargs):
    metadata = json.loads(meta)

    try:
        ui.idle()

        if not ui.infoLabel('Container.FolderPath').startswith('plugin://'):
            ui.PlayList.clear()

        ui.execute('Action(Back,10025)')

        if imdb == '0':
            imdb = '0000000'
        imdb = 'tt' + imdb.translate(None, 't')
        content = 'movie'
        name = '%s (%s)'%(title, year)

        def sources_generator(self):
            def ui_addsources(progress, total, new_results):
                self.addItems(_sources_label(new_results, index=len(self.items)))
                self.updateDialog(progress=(progress, total))
                stop_searching = self.dialog_closed or self.stop_button_flag
                if not stop_searching:
                    ui.sleep(1000)
                return not stop_searching

            providers.video_sources(ui_addsources, content,
                                    title=title, year=year, imdb=imdb, tmdb=tmdb, tvdb=tvdb, meta=meta, **kwargs)

        poster = metadata.get('poster', '0')
        if poster != '0':
            posterdata = 'poster://'+poster
        else:
            poster = platform.addonPoster()
            posterdata = name

        win = ui.SourcesDialog('SourcesDialog.xml', platform.addonPath, 'Default', '720p',
                               sourcesGenerator=sources_generator,
                               sourcePriority=_source_priority,
                               sourceResolve=_resolve,
                               posterData=posterdata)

        # (fixme)[code]: make a ui that is simply called ui.resolvedPlugin()
        if _thread > 0:
            ui.resolvedPlugin(_thread, True, ui.ListItem(path=''))

        while True:
            win.doModal()

            # User-abort
            item = win.selected
            if not item:
                break

            url = item.getProperty('url')

            if win.action == 'play':
                player_status = ui.Player().run(title, year, None, None, imdb, tvdb, meta, url,
                                                credits=_credits_message(item.getProperty('source_provider'),
                                                                         item.getProperty('source_host'),
                                                                         item.getProperty('type')))
                if player_status > 10:
                    break
                if player_status < 0:
                    log.notice('{m}.{f}: %s: %s: invalid source', name, url)
                    source = item.getLabel()
                    ui.infoDialog(_('Not a valid stream'), heading=source)
                    item.setProperty('source_url', '')
                    item.setProperty('url', '')

            elif win.action == 'download':
                media_format = item.getProperty('type')
                try:
                    media_size = int(item.getProperty('size'))
                except Exception:
                    media_size = 0
                rest = item.getProperty('rest') == 'true'

                media_info1 = '' if not media_size else \
                              _('Complete file is %dMB%s')%(int(media_size/(1024*1024)), ' (r)' if rest else '')
                media_info2 = '' if not media_format else \
                              _('Media format is %s')%media_format

                if ui.yesnoDialog(media_info1, media_info2, _('Continue with download?')):
                    if downloader.addDownload(name, url, media_format, media_size, rest, poster):
                        ui.infoDialog(_('Item added to download queue'), name)
                    else:
                        ui.infoDialog(_('Item already in the download queue'), name)

            ui.sleep(2000)

            win.show()

        del win

    except Exception as ex:
        log.error('{m}.{f}: %s', ex)
        ui.infoDialog(_('No stream available'))


@action
def clearsourcescache(name, **kwargs):
    ui.busydialog()
    if name and providers.clear_sources_cache(**kwargs):
        ui.infoDialog(_('Cache cleared for %s')%name)
    ui.idle()


def _credits_message(provider, host, media_format):
    return [
        '[B]~*~ Credits ~*~[/B]',
        'Source provided by [B]%s[/B]'%provider.split('.')[-1].upper(),
        'Content hosted by [COLOR orange]%s[/COLOR]'%host.upper(),
        '%sLoaded in {elapsed_time} seconds'%('' if not media_format else
                                              'Format is [COLOR FF009933]%s[/COLOR]; '%media_format.upper()),
    ]


def _sources_label(sources, index=0):
    for source in sources:
        index += 1

        host = source['source'].lower()
        provider = source['provider'].split('.')[-1]
        quality = source['quality']

        label = '%02d' % index

        if quality in ['1080p', 'HD']:
            label += ' | [B][I]%s [/I][/B]' % (quality)
        else:
            label += ' | [I]%s [/I]' % (quality)

        label += ' | [B]%s[/B] | %s' % (provider, host)

        source['label'] = label.upper()
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
        if (i > _RESOLVER_TIMEOUT and not key_open) or not thd.is_alive():
            break
        if ui_update and not ui_update():
            ui_cancelled = True
            break
        ui.sleep(500)

    for i in range(_RESOLVER_TIMEOUT):
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
