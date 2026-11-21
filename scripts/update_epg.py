import csv
import gzip
import re
import urllib.request
import xml.etree.ElementTree as ET

OUTPUT = "lecy-epg-test.xml"
CATALOGUE = "lecy-channel-ids.csv"
SOURCES = [
    "https://www.open-epg.com/files/unitedkingdom.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://github.com/noodlemctwoodle/epg-guide/releases/latest/download/guide.xml.gz",
    "https://raw.githubusercontent.com/farleyflex/epg-guide/main/epg.xml",
    "https://JohnPulse.github.io/iptv-epg/epg-strong8k.xml.gz",
]
ALIASES = {
    "BBCOneLondon.uk": "bbconelondon.uk",
    "BBCOneLondonHD.uk": "bbconelondon.uk",
    "SkySportsMainEvent.uk": "skysportsmainevent.uk",
    "SkySportsMainEventHD.uk": "skysportsmainevent.uk",
}

def normalise(value):
    value = (value or "").strip().lower()
    value = re.sub(r"(fhd|uhd|hd|sd)(?=\.)", "", value)
    return re.sub(r"[^a-z0-9]", "", value)

with open(CATALOGUE, newline="", encoding="utf-8-sig") as handle:
    lecy_ids = sorted({row["epg_channel_id"].strip() for row in csv.DictReader(handle) if row.get("epg_channel_id", "").strip()})
normalised = {}
for channel_id in lecy_ids:
    normalised.setdefault(normalise(channel_id), []).append(channel_id)

def target_id(source_id):
    if source_id in ALIASES:
        return ALIASES[source_id]
    matches = normalised.get(normalise(source_id), [])
    return matches[0] if len(matches) == 1 else None

merged_channels = {}
merged_programmes = {}
for source_url in SOURCES:
    request = urllib.request.Request(source_url, headers={"User-Agent": "LeCy-EPG-updater/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    source_root = ET.fromstring(payload)
    source_map = {}
    for channel in source_root.findall("channel"):
        source_id = channel.get("id", "")
        destination_id = target_id(source_id)
        if not destination_id:
            continue
        source_map[source_id] = destination_id
        if destination_id not in merged_channels:
            copy = ET.fromstring(ET.tostring(channel, encoding="utf-8"))
            copy.set("id", destination_id)
            merged_channels[destination_id] = copy
    for programme in source_root.findall("programme"):
        destination_id = source_map.get(programme.get("channel", ""))
        if not destination_id:
            continue
        copy = ET.fromstring(ET.tostring(programme, encoding="utf-8"))
        copy.set("channel", destination_id)
        key = (destination_id, copy.get("start", ""), copy.get("stop", ""), copy.findtext("title", ""))
        merged_programmes[key] = copy

root = ET.Element("tv", {
    "generator-info-name": "LeCy multi-source EPG",
    "generator-info-url": "https://github.com/1-dvsbstd/tv-guide-test",
})
for channel_id in sorted(merged_channels):
    root.append(merged_channels[channel_id])
for key in sorted(merged_programmes):
    root.append(merged_programmes[key])
ET.indent(root, space="  ")
ET.ElementTree(root).write(OUTPUT, encoding="utf-8", xml_declaration=True)
