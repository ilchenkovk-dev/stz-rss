import requests
from bs4 import BeautifulSoup
from email.utils import format_datetime
from datetime import datetime, timezone
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

# --------------------------------------------------
# Настройки
# --------------------------------------------------

SOURCE_URL = "https://www.stuttgarter-zeitung.de/stuttgart/"
OUTPUT_FILE = "stuttgart.xml"

MAX_ITEMS = 50

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}

# --------------------------------------------------
# Получаем страницу Stuttgarter Zeitung
# --------------------------------------------------

response = requests.get(
    SOURCE_URL,
    headers=HEADERS,
    timeout=30
)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# --------------------------------------------------
# Создаём RSS
# --------------------------------------------------

rss = ET.Element(
    "rss",
    {
        "version": "2.0",
        "xmlns:atom": "http://www.w3.org/2005/Atom"
    }
)

channel = ET.SubElement(rss, "channel")

ET.SubElement(channel, "title").text = "Stuttgarter Zeitung – Stuttgart"

ET.SubElement(channel, "link").text = SOURCE_URL

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

# --------------------------------------------------
# Ищем статьи
# --------------------------------------------------

articles = []

for article in soup.find_all("article"):

    link_tag = article.find("a", href=True)

    if not link_tag:
        continue

    title_tag = article.find(["h1", "h2", "h3", "h4"])

    if not title_tag:
        continue

    title = title_tag.get_text(" ", strip=True)

    if not title:
        continue

    link = urljoin(SOURCE_URL, link_tag["href"])

    if not link.startswith("https://www.stuttgarter-zeitung.de/"):
        continue

    if link in [item["link"] for item in articles]:
        continue

    description = ""

    paragraph = article.find("p")

    if paragraph:
        description = paragraph.get_text(" ", strip=True)

    articles.append(
        {
            "title": title,
            "link": link,
            "description": description
        }
    )

    if len(articles) >= MAX_ITEMS:
        break

# --------------------------------------------------
# Добавляем статьи в RSS
# --------------------------------------------------

for article in articles:

    item = ET.SubElement(channel, "item")

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

# --------------------------------------------------
# Сохраняем RSS-файл
# --------------------------------------------------

tree = ET.ElementTree(rss)

ET.indent(tree, space="  ")

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print(
    f"RSS создан: {OUTPUT_FILE}. "
    f"Найдено статей: {len(articles)}"
)
