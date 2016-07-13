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


import xbmcgui

from g2.libraries import log
from g2.libraries.language import _


class PackagesDialog(xbmcgui.WindowXMLDialog):
    kinds_listid = 101
    packages_listid = 201

    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback, onPackageSelected, pkgInstalledStatus):
        self.kinds = []
        self.packages = []
        self.kinds_lst = None
        self.packages_lst = None
        self.progress_dialog = None
        self.displayed_kind = None
        self.onPackageSelected = onPackageSelected
        self.pkgInstalledStatus = pkgInstalledStatus

    def addPackage(self, kind, name, desc, site=None):
        item = xbmcgui.ListItem()
        item.setProperty('kind', kind)
        item.setProperty('name', name)
        item.setLabel(desc)
        if site:
            item.setProperty('site', site)
        self.packages.append(item)

    def addKind(self, kind):
        item = xbmcgui.ListItem()
        item.setProperty('kind', kind)
        item.setLabel(kind)
        self.kinds.append(item)

    def onInit(self):
        self.kinds_lst = self.getControl(self.kinds_listid)
        self.packages_lst = self.getControl(self.packages_listid)
        self.kinds_lst.reset()
        self.kinds_lst.addItems(self.kinds)
        for i in self.packages:
            self._update_package_item(i)
        self._update_packages_list('providers')

    def onAction(self, action):
        focus_id = self.getFocusId()
        if focus_id == self.kinds_listid:
            selected_item = self.kinds_lst.getSelectedItem()
            if selected_item:
                self._update_packages_list(selected_item.getLabel().lower())
        xbmcgui.WindowXMLDialog.onAction(self, action)

    def onClick(self, controlID):
        log.debug('{m}.{f}: %s', controlID)
        if controlID == self.kinds_listid:
            kind = self.kinds_lst.getSelectedItem().getLabel().lower()
            self._update_packages_list(kind)

        elif controlID == self.packages_listid:
            item = self.packages_lst.getSelectedItem()
            self.onPackageSelected(item.getProperty('kind'), item.getProperty('name'), item.getProperty('site'))
            self._update_package_item(item)
            self._update_packages_list(force=True)

    def _update_packages_list(self, kind=None, force=False):
        if self.displayed_kind != kind or force:
            if not kind:
                kind = self.displayed_kind
            self.packages_lst.reset()
            self.packages_lst.addItems([i for i in self.packages
                                        if i.getProperty('kind') == kind and
                                        (i.getProperty('site') or
                                         self.pkgInstalledStatus(i.getProperty('kind'), i.getProperty('name')) != 'NotInstalled')])
            self.displayed_kind = kind

    def _update_package_item(self, item):
        status = self.pkgInstalledStatus(item.getProperty('kind'), item.getProperty('name'))
        item.setInfo('video', {
            'overlay': 5 if status != 'NotInstalled' else 4,
        })
        # Indicator in the Package Manager that the package has raised some exceptions
        item.setLabel2(_('[COLOR red]ERR[/COLOR]') if status == 'RaiseException' else
                       # Indicator in the Package Manager that the package has been disabled by the user
                       _('[COLOR orange]DIS[/COLOR]') if status == 'Disabled' else
                       '' if status == 'NotInstalled' else str(status))
