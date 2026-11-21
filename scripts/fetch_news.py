#!/usr/bin/env python3
"""Holt Graz-/Steiermark-News (Google-News-RSS) und schreibt news.json.
Nur Standardbibliothek. Wird stündlich von der GitHub Action ausgeführt."""
import json, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

QUERIES = ['Graz', 'Steiermark']   # Suchbegriffe anpassen
LIMIT = 8                          # Anzahl Meldungen
# Thema -> Stichwörter (erste Übereinstimmung gewinnt)
TOPICS = [
    ('Polizei', r'polizei|festnahme|verdächtig'),
    ('Chronik', r'unfall|brand|einbruch|feuerwehr|überfall'),
    ('Politik', r'gemeinderat|landtag|regierung|bürgermeister|wahl|budget'),
    ('Verkehr', r'verkehr|\bbim\b|\bbus\b|straße|öbb|ticket|stau|mobilität|bahn'),
    ('Sport', r'sturm|\bgak\b|sport|fußball|eishockey|ski'),
    ('Wirtschaft', r'wirtschaft|unternehmen|firma|arbeitsplätz|industrie|jobs'),
    ('Freizeit', r'advent|konzert|theater|festival|markt|ausstellung|kultur'),
    ('Wetter', r'wetter|schnee|glatteis|frost'),
]

def topic(title):
    t = title.lower()
    for name, pattern in TOPICS:
        if re.search(pattern, t):
            return name
    return 'Graz'

def fetch(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode(
        {'q': f'{query} when:2d', 'hl': 'de', 'gl': 'AT', 'ceid': 'AT:de'})
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (jarvis-dashboard)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())

def parse(root):
    for it in root.iter('item'):
        title = (it.findtext('title') or '').strip()
        link = (it.findtext('link') or '').strip()
        src = (it.findtext('source') or '').strip()
        if src and title.endswith(' - ' + src):
            title = title[:-len(' - ' + src)]
        try:
            when = parsedate_to_datetime(it.findtext('pubDate'))
        except Exception:
            when = datetime.fromtimestamp(0, timezone.utc)
        if title and link:
            yield when, title, src or 'News', link

def main():
    found = []
    for q in QUERIES:
        try:
            found += list(parse(fetch(q)))
        except Exception as e:
            print('Fehler bei', q, e)
    found.sort(key=lambda x: x[0], reverse=True)
    seen, items = set(), []
    for when, title, src, link in found:
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append({'title': title, 'source': src, 'link': link, 'topic': topic(title)})
        if len(items) >= LIMIT:
            break
    if not items:
        print('Keine News gefunden - news.json bleibt unverändert.')
        return
    out = {'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'items': items}
    with open('news.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(len(items), 'Meldungen geschrieben.')

if __name__ == '__main__':
    main()
