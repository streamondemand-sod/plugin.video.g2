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


import ast

from g2 import pkg
from g2.libraries import log
from g2.libraries import client2
from g2.libraries import platform
from g2.libraries.language import _

from .lib import ui


_log_debug = True

_DEFAULT_PACKAGES_URLS = ['http://j0rdyz65.github.io/']


def dialog(**kwargs):
    addon_dir = platform.translatePath(platform.addonInfo('path'))
    win = ui.PackagesDialog('PackagesDialog.xml', addon_dir, 'Default', '720p')

    try:
        packages_urls = ast.literal_eval(platform.setting('packages_urls'))
        if not packages_urls:
            raise Exception()
    except Exception:
        packages_urls = _DEFAULT_PACKAGES_URLS

    listed = {}
    kinds = {}
    for url in packages_urls:
        try:
            res = client2.get(url, debug=True)
            pkgentries = client2.parseDOM(res.content, 'tbody')[0]
            pkgentries = client2.parseDOM(pkgentries, 'tr')
        except Exception:
            log.notice('{m}.{f}: %s: no packages directory found', url)
            continue

        for pkgentry in pkgentries:
            try:
                kind, desc, site = client2.parseDOM(pkgentry, 'td')
                log.debug('{m}.{f}: %s %s'%(kind, site))
                if kind not in pkg.kinds():
                    log.notice('{m}.{f}: %s: kind %s not implemented', url, kind)
                    continue
 
                site = site.replace('<code>', '').replace('</code>', '')
                name = pkg.local_name(site)
                if name is None:
                    log.notice('{m}.{f}: %s: site url %s not implemented', url, site)
                    continue

                html_trans = {
                    '<strong>': '[B]',
                    '</strong>': '[/B]',
                }
                for html_code, kodi_code in html_trans.iteritems():
                    desc = desc.replace(html_code, kodi_code)

                item = ui.ListItem()
                item.setLabel(desc)
                item.setProperty('kind', kind)
                item.setProperty('name', name)
                item.setProperty('site', site)
                item.setProperty('installed', 'true' if pkg.is_installed(kind, name) else 'false')
                win.packages.append(item)

                listed[kind+'.'+name] = True
                kinds[kind] = True
            except Exception:
                pass

    for kind, name in pkg.packages():
        if kind+'.'+name not in listed:
            log.notice('{m}.{f}: orphaned package %s.%s'%(kind, name))
            item = ui.ListItem()
            item.setLabel(_('[Orphaned]')+' '+name)
            item.setProperty('kind', kind)
            item.setProperty('name', name)
            item.setProperty('installed', 'true')
            win.packages.append(item)

    for kind in pkg.kinds():
        if kind in kinds:
            item = ui.ListItem()
            item.setLabel(kind.upper())
            win.kinds.append(item)

    win.doModal()

    pkg.update_settings_skema()

    del win
