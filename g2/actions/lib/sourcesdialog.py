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


import datetime

import xbmc
import xbmcgui

from g2.libraries import ui
from g2.libraries import log
from g2.libraries import workers
from g2.libraries import addon
from g2.libraries.language import _

from g2 import defs


class SourcesDialog(xbmcgui.WindowXMLDialog):
    title_label_id = 1
    progress_id = 2
    elapsed_label_id = 3
    progress_label_id = 4
    left_image_id = 11
    left_label_id = 12
    sources_list_id = 21
    counter_label_id = 22
    info_label_id = 23
    select_button_id = 31
    check_button_id = 32
    cancel_button_id = 33

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback,
                 sourceName=None, sourcesGenerator=None, sourcePriority=None, sourceResolve=None, posterImage=None,
                 autoPlay=False):
        self.title_label = None
        self.progress = None
        self.elapsed_label = None
        self.progress_label = None
        self.sources_list = None
        self.counter_label = None
        self.info_label = None
        self.select_button = None
        self.check_button = None
        self.left_image = None
        self.left_label = None

        self.items = []

        self.resolver_lock = workers.Lock()

        self.select_button_focused = False
        self.check_button_flag = True
        self.dialog_closed = False
        self.start_time = None
        self.selected = None
        self.action = None

        self.thread = None
        self.source_name = sourceName
        self.sources_generator = sourcesGenerator
        self.source_priority = sourcePriority
        self.source_resolve = sourceResolve
        self.poster_image = posterImage
        self.auto_play = autoPlay

    def close(self):
        self.dialog_closed = True
        xbmcgui.WindowXMLDialog.close(self)

    def addItems(self, items):
        for source in items:
            item = xbmcgui.ListItem()
            item.setLabel(source['label'])
            item.setIconImage(defs.HOST_IMAGES+source['source'].lower()+'.png')
            item.setProperty('source_provider', source['provider'])
            item.setProperty('source_quality', source['quality'])
            item.setProperty('source_host', source['source'])
            item.setProperty('source_info', source['info'])
            item.setProperty('source_url', source['url'])
            item.setProperty('url', '')
            item.setProperty('resolution', '0')
            self.items.append(item)

    def onInit(self):
        self.select_button_focused = False
        self.check_button_flag = True
        self.dialog_closed = False
        self.start_time = None
        self.selected = None

        self.title_label = self.getControl(self.title_label_id)
        self.sources_list = self.getControl(self.sources_list_id)
        self.counter_label = self.getControl(self.counter_label_id)
        self.info_label = self.getControl(self.info_label_id)
        self.progress = self.getControl(self.progress_id)
        self.elapsed_label = self.getControl(self.elapsed_label_id)
        self.progress_label = self.getControl(self.progress_label_id)
        
        self.select_button = self.getControl(self.select_button_id)
        self._toggle_select_action()

        self.check_button = self.getControl(self.check_button_id)
        self.left_image = self.getControl(self.left_image_id)
        self.left_label = self.getControl(self.left_label_id)

        if self.poster_image:
            self.left_image.setImage(self.poster_image)
            self.left_label.setLabel('')
        else:
            self.left_image.setImage(ui.addon_poster())
            self.left_label.setLabel(self.source_name)

        if not self.thread and self.sources_generator:
            self.thread = workers.Thread(self.sources_worker)
            self.thread.start()
        if not self.thread:
            self.check_button_flag = False

        self.updateDialog(progress='')

    def onClick(self, controlID):
        log.debug('onClick: %s'%controlID)
        if controlID == self.sources_list_id:
            selected = self.sources_list.getSelectedItem()
        elif controlID == self.select_button_id:
            selected = self.sources_list.getListItem(0)
        elif controlID == self.cancel_button_id:
            self.selected = None
            self.close()
            return
        elif controlID == self.check_button_id:
            if not self.thread:
                self.thread = workers.Thread(self.sources_worker)
                self.thread.start()
            else:
                self.check_button_flag = False
            return
        else:
            return
        while not selected.getProperty('url'):
            xbmc.executebuiltin('ActivateWindow(busydialog)')
            self.resolver(selected)
            if selected.getProperty('url'):
                break
            self.updateDialog()
            if controlID == self.select_button_id:
                selected = self.sources_list.getListItem(0)
            else:
                xbmcgui.Dialog().notification(addon.addonInfo('name'), _('Source not valid'),
                                              ui.addon_icon(), 3000, sound=False)
                xbmc.executebuiltin('Dialog.Close(busydialog)')
                return
        xbmc.executebuiltin('Dialog.Close(busydialog)')
        self.selected = selected
        self.close()

    def onAction(self, action):
        focus_id = self.getFocusId()
        if focus_id == self.sources_list_id:
            self.info_label.setLabel(self.sources_list.getSelectedItem().getProperty('source_info'))
        elif focus_id == self.select_button_id:
            if action.getId() == 10:
                return
            elif action.getId() == 101:
                self._toggle_select_action()
                return
        xbmcgui.WindowXMLDialog.onAction(self, action)

    def _toggle_select_action(self):
        if self.action != 'play':
            self.select_button.setLabel(_('Play'))
            self.action = 'play'
        else:
            self.select_button.setLabel(_('Download'))
            self.action = 'download'

    def onFocus(self, controlID):
        log.debug('onFocus: %s'%controlID)
        if controlID == self.select_button_id:
            self.sources_list.selectItem(0)

    def userStopped(self):
        return self.dialog_closed or not self.check_button_flag

    def sources_worker(self):
        if self.sources_generator:
            log.debug('sources.dialog: sources_worker: calling the source generator function')
            self.updateDialog(title=_('SEARCHING SOURCES'), elapsed_time=True)
            self.sources_generator(self)
            self.sources_generator = None

        log.debug('sources.dialog: sources_worker: %d url listed, %d already processed (OK/KO: %d/%d)',
                  len(self.items),
                  len([i for i in self.items if i.getProperty('url') or not i.getProperty('source_url')]),
                  len([i for i in self.items if i.getProperty('url')]),
                  len([i for i in self.items if not i.getProperty('source_url')]))

        if not len(self.items):
            self.check_button_flag = False
            self.updateDialog(title=_('NO SOURCES FOUND'), elapsed_time=False)
            return

        self.check_button_flag = True
        self.updateDialog(title=_('CHECKING SOURCES'), elapsed_time=True)

        all_sources_resolved = False
        while not self.userStopped():
            all_sources_resolved = True
            for index in range(len(self.items)):
                try:
                    item = self.sources_list.getListItem(index)
                except Exception:
                    break
                if item.getProperty('source_url') and not item.getProperty('url'):
                    all_sources_resolved = False
                    break
            if all_sources_resolved:
                break

            self.resolver(item)
            if self.auto_play and item.getProperty('url'):
                self.selected = item
                self.close()
                break

            self.updateDialog()
            xbmc.sleep(500)

        self.check_button_flag = False
        if all_sources_resolved:
            title = _('SELECT SOURCE')
            progress = _('CHECKING COMPLETE')
        else:
            title = None
            progress = _('CHECKING STOPPED')

        self.updateDialog(title=title, progress=progress, elapsed_time=False)

        log.debug('sources.dialog: sources_worker stopped (%s): %d url listed, %d processed (OK/KO: %d/%d)',
                  'DIALOG CLOSED' if self.dialog_closed else progress,
                  len(self.items),
                  len([i for i in self.items if i.getProperty('url') or not i.getProperty('source_url')]),
                  len([i for i in self.items if i.getProperty('url')]),
                  len([i for i in self.items if not i.getProperty('source_url')]))

        self.thread = None

    def resolver(self, item):
        if not self.source_resolve:
            item.setProperty('url', item.getProperty('source_url'))
            return
        # Ensure that only one thread is resolving
        with self.resolver_lock:
            provider = item.getProperty('source_provider')
            url = item.getProperty('source_url')
            label = item.getLabel()
            label_fmt = '[COLOR FF009933][%s][/COLOR] %s'
            self.ellipsis = 0
            def item_label_update():
                self.ellipsis %= 3
                self.ellipsis += 1
                item.setLabel(label_fmt%('.' * self.ellipsis, label))
                return not self.dialog_closed

            item_label_update()
            thd = self.source_resolve(provider, url, ui_update=item_label_update)

            # NOTE: a URL is considered not resolved if:
            # - The resolver thread has been cancelled or
            # - The resolver thread is still running (hence it timeout) or
            # - The resolver failed the resolution or
            # - The url resolved to plugin://
            if not thd or thd.is_alive() or not thd.result or thd.result.startswith('plugin://'):
                item.setProperty('source_url', '')
            else:
                url = thd.result
                item.setProperty('url', url)
                media_label = '?'
                if hasattr(url, 'meta') and url.meta:
                    if url.meta.get('type'):
                        media_label = url.meta['type']
                        item.setProperty('type', media_label)
                    if url.meta.get('width') > 0 and url.meta.get('height') > 0:
                        media_label += ' %sx%s'%(url.meta['width'], url.meta['height'])
                        item.setProperty('resolution', str(url.meta['width']*url.meta['height']))
                    item.setProperty('format', media_label)

                if hasattr(url, 'size'):
                    size_mb = int(url.size / (1024*1024))
                    media_label += ' %dMB'%size_mb if size_mb < 1000 else ' %.1fGB'%(size_mb/1024)
                    item.setProperty('size', str(url.size))

                if hasattr(url, 'acceptbyteranges') and url.acceptbyteranges:
                    item.setProperty('rest', 'true')

                item.setLabel(label_fmt%(media_label.upper(), label))

            log.debug('{m}.{f}: %s: %s'%(label, 'OK' if item.getProperty('url') else 'KO'))

    def updateDialog(self, title=None, progress=None, elapsed_time=None):
        if title:
            self.title_label.setLabel(title)

        if elapsed_time is not None:
            self.start_time = None if not elapsed_time else datetime.datetime.now()
        self.elapsed_label.setLabel('' if not self.start_time else '%ds'%(datetime.datetime.now()-self.start_time).seconds)

        if progress is None:
            progress = len([i for i in self.items if i.getProperty('url') or not i.getProperty('source_url')])
            total = len(self.items)
        elif type(progress) in [list, tuple]:
            progress, total = progress
        else:
            total = None
        if total:
            self.progress.setPercent(100 * progress / total)
            self.progress_label.setLabel('%d / %d'%(progress, total))
        elif progress:
            self.progress_label.setLabel(progress)

        items_active = [i for i in self.items if i.getProperty('source_url')]
        last_selected_position = self.sources_list.getSelectedPosition()
        self.sources_list.reset()
        if callable(self.source_priority):
            items_active = sorted(items_active,
                                  key=lambda i:
                                  self.source_priority(i.getProperty('source_host'),
                                                       i.getProperty('source_provider'),
                                                       i.getProperty('source_quality'),
                                                       int(i.getProperty('resolution'))),
                                  reverse=True)
        self.sources_list.addItems(items_active)
        if last_selected_position >= 0:
            self.sources_list.selectItem(last_selected_position)

        if self.items and not items_active:
            self.title_label.setLabel('NO VALID SOURCES')

        self.counter_label.setLabel('' if len(items_active) <= 10 else '%d'%len(items_active))

        self.select_button.setEnabled(len(items_active) > 0)
        if len(items_active) > 0 and not self.select_button_focused:
            self.setFocus(self.select_button)
            self.select_button_focused = True

        if self.check_button_flag:
            # Label for the button that stops the sources validation
            self.check_button.setLabel(_('Stop'))
            self.check_button.setEnabled(True)
        else:
            # Label for the button that starts the sources validation
            self.check_button.setLabel(_('Check'))
            items_2resolve = [i for i in self.items if not i.getProperty('url') and i.getProperty('source_url')]
            self.check_button.setEnabled(len(items_2resolve) > 0)
