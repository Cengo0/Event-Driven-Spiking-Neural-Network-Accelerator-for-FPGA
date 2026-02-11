#!/usr/bin/env python3
import xml.etree.ElementTree as ET, sys

tree = ET.parse(sys.argv[1])
root = tree.getroot()
ns = {'spirit': 'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009'}

for mm in root.iter('{http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009}memoryMap'):
    name = mm.find('spirit:name', ns)
    if name is not None:
        for ab in mm.findall('.//spirit:addressBlock', ns):
            bn = ab.find('spirit:name', ns)
            ba = ab.find('spirit:baseAddress', ns)
            rng = ab.find('spirit:range', ns)
            if bn is not None and ba is not None:
                print(f'{name.text}: {bn.text} base={ba.text} range={rng.text if rng is not None else "?"}')
