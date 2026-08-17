import requests
from bs4 import BeautifulSoup
from email.utils import format_datetime
from datetime import datetime, timezone
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

SOURCE_URL = "https://www.stuttgarter-zeitung.de/lokales/stuttgart/"
OUTPUT_FILE = "stuttgart.xml"

MAX_ITEMS = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}

response = requests.get(
    SOURCE_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

rss = ET.Element(
    "rss",
    {
        "version": "2.0",
        "xmlns:atom": "http://www.w3.org/2005/Atom"
    }
)

channel = ET.SubElement(rss, "channel")

ET.SubElement(
    channel,
    "title"
).text = "Stuttgarter Zeitung – Stuttgart"

ET.SubElement(
    channel,
    "link"
).text = SOURCE_URL

ET.SubElement(
    channel,
    "description"
).text = "Aktuelle Nachrichten aus Stuttgart – Stuttgarter Zeitung"

ET.SubElement(
    channel,
    "language"
).text = "de-DE"

ET.SubElement(
    channel,
    "lastBuildDate"
).text = format_datetime(
    datetime.now(timezone.utc)
)

articles = []
seen_links = set()

for link_tag in soup.find_all("a", href=True):

    href = link_tag["href"]

    link = urljoin(SOURCE_URL, href)

    if not link.startswith(
        "https://www.stuttgarter-zeitung.de/"
    ):
        continue

    if link in seen_links:
        continue

    title_tag = link_tag.find(
        ["h1", "h2", "h3", "h4"]
    )

    if title_tag:
        title = title_tag.get_text(
            " ",
            strip=True
        )
    else:
        title = link_tag.get_text(
            " ",
            strip=True
        )

    if not title:
        continue

    if len(title) < 15:
        continue

    if len(title) > 250:
        continue

    if link.rstrip("/") == SOURCE_URL.rstrip("/"):
        continue

    articles.append(
        {
            "title": title,
            "link": link,
            "description": ""
        }
    )

    seen_links.add(link)

    if len(articles) >= MAX_ITEMS:
        break

for article in articles:

    item = ET.SubElement(
        channel,
        "item"
    )

    ET.SubElement(
        item,
        "title"
    ).text = article["title"]

    ET.SubElement(
        item,
        "link"
    ).text = article["link"]

    ET.SubElement(
        item,
        "guid",
        {"isPermaLink": "true"}
    ).text = article["link"]

    ET.SubElement(
        item,
        "description"
    ).text = article["description"]

tree = ET.ElementTree(rss)

ET.indent(
    tree,
    space="  "
)

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print(
    f"RSS erstellt: {OUTPUT_FILE}. "
    f"Gefundene Artikel: {len(articles)}"
)
