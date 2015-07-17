Mapfile: Python library for parsing MSVC-generated linker map files
===================================================================

Tested with MSVC 2010 linker map files only. YMMV. Pull requests
welcome.


Example usage
-------------

>>> import mapfile
>>> mf = mapfile.parse_mapfile('my_program.map')
>>> print str(mr)
module:                 my_program
preferred_load_address: 0x0000000000400000
# of sections:          40
# of symbols:           250669

>>> candidates = mf.filter_symbols('?HelloWorld@')
>>> [str(c) for c in candidates]
['Symbol: ?HelloWorld@']
