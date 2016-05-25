# -*- coding: utf-8 -*-

"""
    Genesi2 Add-on
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

import ast

import xbmc
import xbmcaddon
import xbmcgui

import g2

from g2.libraries import log
from g2.libraries import client
from g2.libraries import platform
from g2.libraries.language import _
from .lib import ui


_DEFAULT_PACKAGES_URLS = ['https://github.com/J0rdyZ65/plugin.video.g2/wiki']


# TODO[logic]: fix according to the new packages api and kind names...
# TODO[code]: move PackagesDialog class to resources.lib.ui.kodi.g2.py
class PackagesDialog(xbmcgui.WindowXMLDialog):
    sources_buttonid = 101
    resolvers_buttonid =102
    packages_listid =201

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):
        self.__kind = None
        self.items = []

    def onInit(self):
        self.lst = self.getControl(self.packages_listid)
        self._renderitems('sources')
        self.setFocusId(self.sources_buttonid)

    def onClick(self, controlID):
        if controlID == self.sources_buttonid:
            self._renderitems('sources')
        elif controlID == self.resolvers_buttonid:
            self._renderitems('resolvers')
        elif controlID == self.packages_listid:
            item = self.lst.getSelectedItem()
            kind = item.getProperty('kind')
            name = item.getProperty('name')
            if not g2.is_installed(kind, name):
                self.progress_dialog = ui.DialogProgressBG()
                self.progress_dialog.create(_('Download Package')+' '+name)
                self._update_progress_dialog(0)
                if g2.install_or_update(kind, name, item.getProperty('site'), self._update_progress_dialog):
                    _setListItemInstalledStatus(item, True)
                self.progress_dialog.close()
            elif ui.yesnoDialog(_('Are you sure?'), '', '', heading=_('Uninstall Package')+' '+name) and g2.uninstall(kind, name):
                _setListItemInstalledStatus(item, False)
                if not item.getProperty('site'):
                    self.items = [i for i in self.items if i.getProperty('kind') != kind or i.getProperty('name') != name]
                    self._renderitems(force=True)

    def _update_progress_dialog(self, curitem, numitems=1):
        self.progress_dialog.update(curitem*100/(numitems if numitems else 1))

    def _renderitems(self, kind=None, force=False):
        if self.__kind != kind or force:
            if not kind: kind = self.__kind
            self.lst.reset()
            self.lst.addItems([i for i in self.items if i.getProperty('kind') == kind])
            self.lst.selectItem(0)
            self.__kind = kind


def _setListItemInstalledStatus(listItem, installed):
    if str(installed) != listItem.getProperty('installed'):
        listItem.setProperty('installed', str(installed))
        listItem.setInfo('video', {'overlay': 5 if installed else 4})


def dialog(**kwargs):
    addon_dir = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
    w = PackagesDialog('PackagesDialog.xml', addon_dir, 'Default', '720p')

    try:
        packages_urls = ast.literal_eval(platform.setting('packages_urls'))
        if not packages_urls: raise Exception()
    except:
        packages_urls = _DEFAULT_PACKAGES_URLS

    listed = {}
    for url in packages_urls:
        try:
            r = client.request(url)
            r = client.parseDOM(r, 'table', attrs={'name': 'user-content-packages'})[0]
            r = client.parseDOM(r, 'tr')
        except:
            continue
        for package in r:
            try:
                kind, description, site = client.parseDOM(package, 'td', noattrs=False)
                log.notice('g2.dialog: %s: %s@%s'%(url, kind, site))
                if kind not in ['sources', 'resolvers']: continue
                name = g2.local_name(site)
                if name is None: continue
                item = ui.ListItem()
                item.setLabel(description)
                _setListItemInstalledStatus(item, g2.is_installed(kind, name))
                item.setProperty('kind', kind)
                item.setProperty('name', name)
                item.setProperty('site', site)
                w.items.append(item)
                listed[kind+'.'+name] = True
            except:
                pass

    for kind, name in g2.packages():
        if kind+'.'+name not in listed:
            log.notice('g2.dialog: Orphaned: %s.%s'%(kind, name))
            item = ui.ListItem()
            item.setLabel(_('[Orphaned]')+' '+name)
            _setListItemInstalledStatus(item, True)
            item.setProperty('kind', kind)
            item.setProperty('name', name)
            w.items.append(item)

    w.doModal()

    g2.update_settings_skema()

    del w
