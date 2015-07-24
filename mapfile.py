#
# Parses a MSVC mapfile
#
import re
import sys


class MapFileParser:
    @staticmethod
    def handle_preferred_load_addr(data, mf):
        regex = re.compile('Preferred load address is ([0-9]{8,16})')
        group = re.search(regex, data[0])
        mf.preferred_load_addr = int(group.group(1), 16)
        return 2  # advance by two lines

    @staticmethod
    def handle_sections(data, mf):
        # advance past header
        data = data[1:]
        index = 0
        regex = re.compile('([0-9]{4}):[0-9a-fA-F]{8} '  # section index
                           '([0-9a-fA-F]{8})H '          # section length
                           '(.+)\s+'                     # section name
                           '([A-Z]+)'                    # section type
                                                         #  (eg. CODE, DATA)
                           )
        while len(data[index]) != 0 and data[index] != '\n':
            group = re.search(regex, data[index])
            if group is None:
                continue

            mf.add_section(int(group.group(1), 16),
                           int(group.group(2), 16),
                           group.group(3).strip(),
                           group.group(4).strip())
            index = index + 1
        return index + 1

    @staticmethod
    def handle_symbols(data, mf):
        # advance past header
        data = data[2:]
        index = 0
        regex = re.compile('([0-9a-fA-F]{4}):'       # section index
                           '([0-9a-fA-F]{8})\s+'     # offset within section
                           '(.+)\s+'                 # symbol name
                           '([0-9a-fA-F]{8,16})\s+'  # rva+base
                           '(.+)'                    # cruft + object file
                           )
        while index < len(data) and \
                len(data[index]) != 0 and \
                data[index] != '\n':
            group = re.search(regex, data[index])
            if group is None:
                break

            mf.add_symbol(int(group.group(1).strip(), 16),
                          int(group.group(2).strip(), 16),
                          group.group(3).strip(),
                          int(group.group(4).strip(), 16),
                          group.group(5).strip(),
                          group.group(0).strip())

            index = index + 1
        return index + 1


class MapFile(object):
    class Section(object):
        def __init__(self, index, length, name, type):
            self.index = index
            self.length = length
            self.name = name
            self.type = type

        def __str__(self):
            return '{0} section:\n' \
                '  name: {1}\n' \
                '  index: {2:04x}:{3:08x}'.format(self.type,
                                                  self.name,
                                                  self.index,
                                                  self.length)

    class Symbol(object):
        def __init__(self, index, offset, name, rva_base, object_file,
                     original_entry):
            self.section_index = index
            self.section_offset = offset
            self.name = name
            self.rva_base = rva_base
            self.object_file = object_file
            self.original_entry = original_entry

        def __str__(self):
            return 'Symbol: {0}'.format(self.name)

    def __init__(self):
        self.entry_point = None
        self.preferred_load_addr = None
        self.sections = []
        self.symbols = []
        self.module_name = None

    def __str__(self):
        return 'module:                 {0}\n' \
               'preferred_load_address: 0x{1:016x}\n' \
               '# of sections:          {2}\n' \
               '# of symbols:           {3}\n'.format(self.module_name,
                                                      self.preferred_load_addr,
                                                      len(self.sections),
                                                      len(self.symbols))

    def add_section(self, index, length, name, type):
        section = MapFile.Section(index, length, name, type)
        self.sections.append(section)

    def add_symbol(self, index, offset, name, rva_base, object_file,
                   original_entry):
        symbol = MapFile.Symbol(index, offset, name, rva_base,
                                object_file, original_entry)
        self.symbols.append(symbol)

    def filter_symbols(self, search_symbol, search_hint=None):
        #matches = [x for x in self.symbols
        #           if re.search(search_symbol, x.name) is not None]
        matches = []
        for x in self.symbols:
            if x.name.find(search_symbol) != -1:
                matches.append(x)

        if len(matches) > 1 and search_hint is not None:
            matches = [x for x in matches
                       if x.original_entry.find(search_hint) != -1]
        return matches

    def get_symbol_rva(self, symbol):
        return symbol.rva_base - self.preferred_load_addr


def parse_mapfile(mapfile, show_skipped_sections=False):
    handlers = [
        ('Preferred load address is ([0-9]{8,16})',
            MapFileParser.handle_preferred_load_addr),
        ('Start\s+Length\s+Name\s+Class',
            MapFileParser.handle_sections),
        ('Address\s+Publics by Value\s+Rva\+Base\s+Lib:Object',
            MapFileParser.handle_symbols),
        ('Static symbols',
            MapFileParser.handle_symbols)
    ]

    # read file content from mapfile
    def get_file_contents(file):
        with open(file, 'r') as f:
            return f.readlines()

    data = get_file_contents(mapfile)
    mapfile = MapFile()

    # manually extract first line as module name
    mapfile.module_name = data[0].strip()

    # scan through mapfile contents to parse out the remaining sections
    index = 0
    while index < len(data) and len(handlers):
        handler = handlers[0]
        line = data[index]

        if not re.search(handler[0], line):
            index = index + 1
            if line != '\n' and show_skipped_sections:
                print >> sys.stderr, "skipped section: {0}".format(
                    line)
            continue

        index = index + handler[1](data[index:], mapfile)
        handlers = handlers[1:]

    return mapfile


if __name__ == "__main__":
    def file_exists(f):
        import os
        if os.access(f, os.F_OK):
            return f
        raise argparse.ArgumentTypeError()

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mapfile',
                        type=file_exists,
                        help='Mapfile to locate symbols in')

    args = parser.parse_args()

    # read file content from mapfile
    mapfile = parse_mapfile(args.mapfile, True)

    print str(mapfile)
