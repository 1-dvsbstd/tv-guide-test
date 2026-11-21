import gzip
import urllib.request
import xml.etree.ElementTree as ET

SOURCE = "https://www.open-epg.com/files/unitedkingdom.xml.gz"
OUTPUT = "lecy-epg-test.xml"

# Only confirmed LeCy-compatible corrections belong here.
ID_MAP = {
    "BBCOneLondon.uk": "bbconelondon.uk",
    "SkySportsMainEvent.uk": "skysportsmainevent.uk",
}

with urllib.request.urlopen(SOURCE, timeout=60) as response:
    data = gzip.decompress(response.read())

root = ET.fromstring(data)

for channel in root.findall("channel"):
    old_id = channel.get("id")
    if old_id in ID_MAP:
        channel.set("id", ID_MAP[old_id])

for programme in root.findall("programme"):
    old_id = programme.get("channel")
    if old_id in ID_MAP:
        programme.set("channel", ID_MAP[old_id])

ET.indent(root, space="  ")
tree = ET.ElementTree(root)
tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)
