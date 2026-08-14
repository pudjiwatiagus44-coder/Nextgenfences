#!/usr/bin/env python3
import os
import struct
import zlib
import argparse

MAGIC = b'PYZ\0'

class CArchive:
    def __init__(self, path):
        self.path = path
        self.table_of_contents = []
        self.extract_path = None

    def unpack(self):
        with open(self.path, "rb") as fp:
            if fp.read(4) != b'PYI\0':
                raise ValueError('Not a PyInstaller archive')
            fp.read(8)  # length of package
            toc_offset = struct.unpack('!i', fp.read(4))[0]
            fp.seek(toc_offset, os.SEEK_SET)
            length = struct.unpack('!i', fp.read(4))[0]
            self.table_of_contents = []
            for _ in range(length):
                entry = self._read_entry(fp)
                self.table_of_contents.append(entry)

    def _read_entry(self, fp):
        dpos, dlen = struct.unpack('!ii', fp.read(8))
        cflag = struct.unpack('!i', fp.read(4))[0]
        name_len = struct.unpack('!i', fp.read(4))[0]
        name = fp.read(name_len).decode('utf-8')
        return {'dpos': dpos, 'dlen': dlen, 'cflag': cflag, 'name': name}

    def extract(self, outdir, target=None):
        self.extract_path = outdir
        os.makedirs(outdir, exist_ok=True)
        with open(self.path, "rb") as fp:
            for entry in self.table_of_contents:
                if target and entry['name'] != target:
                    continue
                fp.seek(entry['dpos'], os.SEEK_SET)
                data = fp.read(entry['dlen'])
                if entry['cflag']:
                    data = zlib.decompress(data)
                outpath = os.path.join(outdir, entry['name'])
                os.makedirs(os.path.dirname(outpath), exist_ok=True)
                with open(outpath, 'wb') as ofp:
                    ofp.write(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('--extract', dest='extract', help='member to extract')
    parser.add_argument('--out', dest='out', default='extracted')
    args = parser.parse_args()

    car = CArchive(args.archive)
    car.unpack()
    car.extract(args.out, args.extract)

if __name__ == '__main__':
    main()
