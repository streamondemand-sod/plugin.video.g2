# -*- coding: utf-8 -*-

"""
    Genesi2 Add-on
    Based on the original idea/code of boogiekodi@GitHub for his ump plugin
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
import struct


def video_resolution(file, stop_at_bytes=0):
    file.read(5)
    b1, b2, b3 = struct.unpack("3B", file.read(3))      # payload size of the 1st packet (typically the metadata header)
    size = (b1 << 16) + (b2 << 8) + b3
    file.read(7)    # Skip the rest of the packet header
    file.read(4)    # Skip first uint32 of the payload content
    header = file.read(size-4)
    width = re.findall(r'width.(........)', header)
    height = re.findall(r'height.(........)', header)

    return (int(struct.unpack(">d",width[0])[0]) if width else 0, int(struct.unpack(">d",height[0])[0]) if height else 0)
