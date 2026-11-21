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
    value = (value or "").lower()
    value = re.sub(r"\([^)]*(fhd|uhd|hd|sd|1080p|720p|576p|5\.1)[^)]*\)", "", value)
    value = re.sub(r"\b(fhd|uhd|hd|sd|1080p|720p|576p|5\.1)\b", "", value)
    value = value.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", value)

with open(CATALOGUE, newline="", encoding="utf-8-sig") as handle:
    rows = list(csv.DictReader(handle))

lecy_ids = sorted({row["epg_channel_id"].strip() for row in rows if row.get("epg_channel_id", "").strip()})
normalised_ids = {}
for channel_id in lecy_ids:
    normalised_ids.setdefault(normalise(channel_id), []).append(channel_id)

name_candidates = {}
for row in rows:
    channel_id = row.get("epg_channel_id", "").strip()
    channel_name = row.get("name", "").strip()
    if channel_id and channel_name:
        name_candidates.setdefault(normalise(channel_name), set()).add(channel_id)

name_map = {key: next(iter(values)) for key, values in name_candidates.items() if len(values) == 1}

def target_id(source_id, display_name):
    if source_id in ALIASES:
        return ALIASES[source_id]
    id_matches = normalised_ids.get(normalise(source_id), [])
    if len(id_matches) == 1:
        return id_matches[0]
    return name_map.get(normalise(display_name))

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
        display_name = channel.findtext("display-name", "")
        destination_id = target_id(source_id, display_name)
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
