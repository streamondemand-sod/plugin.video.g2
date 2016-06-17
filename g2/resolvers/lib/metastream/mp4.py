# -*- coding: utf-8 -*-

"""
    G2 Add-on
    Copyright 2015 charsyam@GitHub

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


import struct


class NotMP4FormatException(Exception):
    pass
 
 
class ATOM(object):
    def __init__(self, size, name, pos):
        self.size = size
        self.name = name
        self.pos = pos
        self.children = []
        self.properties = None
 
    def find_child_atom_internal(self, atoms, part_arr):
        name = part_arr[0]
        for atom in atoms:
            if atom.name == name:
                if len(part_arr) == 1:
                    return atom
 
                return self.find_child_atom_internal(atom.children, part_arr[1:])
 
        return None
 
    def find_child_atom(self, name):
        part_arr = name.split("/")
        return self.find_child_atom_internal(self.children, part_arr)
 
    def __str__(self):
        return "%s(%s) @%s Props=%s"%(self.name, self.size, self.pos, self.properties)
 
    def __repr__(self):
        return self.__str__()
 
 
class MP4(object):
    def __init__(self, file):
        self.file = file
        self.file_offset = 0
        self.children = []


    def file_read(self, size):
        rbytes = self.file.read(size)
        self.file_offset += len(rbytes)
        return rbytes


    def file_seek(self, pos):
        if pos < self.file_offset:
            raise NotMP4FormatException()
        self.file_read(pos - self.file_offset)


    def is_parent_atom(self, name):
        return name not in ['mdat', 'tkhd', 'vmhd']

 
    def create_empty_atom(self):
        return ATOM(0, "", 0)

 
    def find_atom(self, name):
        for atom in self.children:
            if atom.name == name:
                return atom
        return None


    def parse(self, stop_at_atom=None, stop_at_bytes=0):
        try:
            next_pos = 0
            while True:
                atom = self.parse_internal(next_pos, 0, stop_at_bytes)
                if atom.size <= 0:
                    break
                self.children.append(atom)
                if atom.name == stop_at_atom:
                    break
                next_pos += atom.size

        except struct.error:
            pass

        except:
            return False

        return True


    def get_atom(self, pos):
        self.file_seek(pos)
        size = struct.unpack('>i', self.file_read(4))[0]
        name = self.file_read(4)
        return ATOM(size, name, pos)

 
    def parse_avcC(self, avc, name, size):
        avcC = {}
        spss = []
        ppss = []
        version = struct.unpack('>b', self.file_read(1))[0]
        avc_profile_idc = struct.unpack('>b', self.file_read(1))[0]
        profile_compatibility = struct.unpack('>b', self.file_read(1))[0]
        avc_level_idc = struct.unpack('>b', self.file_read(1))[0]
 
        lengh_size_minus_one = (struct.unpack('>b', self.file_read(1))[0]) & 0x03 + 1
        num_of_sps = (struct.unpack('>b', self.file_read(1))[0]) & 0x1F
        for i in range(num_of_sps):
            length_sps = struct.unpack('>h', self.file_read(2))[0]
            sps = self.file_read(length_sps)
            spss.append(sps)
 
        num_of_pps = struct.unpack('>b', self.file_read(1))[0]
        for i in range(num_of_pps):
            length_pps = struct.unpack('>h', self.file_read(2))[0]
            pps = self.file_read(length_pps)
            ppss.append(pps)
        
        avcC["length_size_minus_one"] = lengh_size_minus_one
        avcC["sps"] = spss
        avcC["pps"] = ppss
        return avcC

 
    def parse_avc_internal(self, atom):
        avc = {}
        size = struct.unpack('>i', self.file_read(4))[0]
        name = self.file_read(4)
        if name != "avc1":
            return None
 
        avc["name"] = name
        self.file_read(24)
        avc["w"] = struct.unpack('>h', self.file_read(2))[0]
        avc["h"] = struct.unpack('>h', self.file_read(2))[0]
        avc["hres"] = struct.unpack('>i', self.file_read(4))[0]
        avc["vres"] = struct.unpack('>i', self.file_read(4))[0]
        self.file_read(4)
 
        frame_count = struct.unpack('>h', self.file_read(2))[0]
        if frame_count != 1:
            return None
 
        self.file_read(32)
        depth = struct.unpack('>h', self.file_read(2))[0]
        if depth != 0x18:
            return None
 
        pd = struct.unpack('>h', self.file_read(2))[0]
        if pd != -1:
            return None
 
        while True:
            tsize = struct.unpack('>i', self.file_read(4))[0]
            tname = self.file_read(4)
 
            if tname == "avcC":
                avc["avc"] = self.parse_avcC(avc, tname, tsize)
                break
            else:
                self.file_read(tsize-8)
        
        return avc

 
    def parse_avc(self, atom):
        self.file_seek(atom.pos+12)
        entry_count = struct.unpack('>i', self.file_read(4))[0]
        entries = []
 
        for i in range(entry_count):
            entry = self.parse_avc_internal(atom)
            if entry is not None:
                entries.append(entry)
 
        return entries
        
 
    def parse_internal(self, pos, total_size=0, stop_at_bytes=0):
        if stop_at_bytes > 0 and pos > stop_at_bytes:
            return self.create_empty_atom()

        atom = self.get_atom(pos)
        if total_size > 0 and atom.size > total_size:
            return self.create_empty_atom()
 
        if self.is_parent_atom(atom.name) == False:
            return atom
 
        if atom.name == "stsd":
            child = self.parse_avc(atom)
            atom.properties = child
            return atom
 
        next_pos = atom.pos + 8
        temp_size = atom.size
 
        while (next_pos+8) < (atom.pos + atom.size):
            child = self.parse_internal(next_pos, atom.size, stop_at_bytes)
            if (child.size >= atom.size) or child.size <= 0:
                break
 
            atom.children.append(child)
            next_pos += child.size
 
        return atom

 
def video_resolution(file, stop_at_bytes=0):
    mp4 = MP4(file)
    if not mp4.parse(stop_at_atom='moov', stop_at_bytes=stop_at_bytes):
        return (-1, -1)

    def traverse(atoms, depth=0):
        from g2.libraries import log
        for atom in atoms:
            log.debug('mp4.video_resolution: %s%s'%('    ' * depth, atom))
            traverse(atom.children, depth+1)
    traverse(mp4.children)      # debugging mp4 decoding...

    moov_atom = mp4.find_atom('moov')
    if not moov_atom:
       return (0, 0)
    for atom in moov_atom.children:
        if atom.name == 'trak':
            stsd_atom = atom.find_child_atom('mdia/minf/stbl/stsd')
            if stsd_atom:
                for prop in stsd_atom.properties:
                    if 'w' in prop or 'h' in prop:
                        return (prop.get('w', 0), prop.get('h', 0))

    return (0, 0)

 
if __name__ == "__main__":
    import os
    import sys

    if len(sys.argv) < 2:
        print("%s [filename]"%(sys.argv[0]))
        sys.exit(0)

    with open(sys.argv[1], 'rb') as f:
        mp4 = MP4(f)
        if not mp4.parse(stop_at_atom='moov', stop_at_bytes=500*1024) or not mp4.find_atom('ftyp'):
            print 'Nor an MP4 file'
            sys.exit(1)

        print 'MP4'

        def traverse(atoms, depth=0):
            for atom in atoms:
                print "%s%s"%('    ' * depth, atom)
                traverse(atom.children, depth+1)
        traverse(mp4.children)

        moov_atom = mp4.find_atom('moov')
        if moov_atom:
            for atom in moov_atom.children:
                if atom.name == "trak":
                    stsd_atom = atom.find_child_atom('mdia/minf/stbl/stsd')
                    if stsd_atom:
                        for prop in stsd_atom.properties:
                            if 'h' in prop and 'w' in prop:
                                print '%sx%s'%(prop['w'], prop['h'])
                                break

        print 'Read %s bytes of %d'%(f.tell(), os.path.getsize(sys.argv[1]))
