import requests
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape
from urllib.parse import urljoin
import time


SOURCE_URL = "https://www.stuttgarter-zeitung.de/wirtschaft/"
OUTPUT_FILE = "wirtschaft.xml"
MAX_ITEMS = 30

headers = {
    "User-Agent": "Mozilla/5.0"
}


# --------------------------------------------------
# Загружаем страницу Wirtschaft
# --------------------------------------------------

response = requests.get(
    SOURCE_URL,
    headers=headers,
    timeout=20
)

response.raise_for_status()

soup = BeautifulSoup(
    response.text,
    "html.parser"
)


# --------------------------------------------------
# Собираем статьи
# --------------------------------------------------

items = []
seen = set()

for a in soup.find_all("a", href=True):

    href = a.get("href")

    if not href:
        continue

    link = urljoin(
        SOURCE_URL,
        href
    )

    # Настоящие статьи StZ имеют URL .html
    if not link.endswith(".html"):
        continue

    # Только сайт Stuttgarter Zeitung
    if not link.startswith(
        "https://www.stuttgarter-zeitung.de/"
    ):
        continue

    # Защита от дублей
    if link in seen:
        continue

    seen.add(link)


    # ------------------------------------------------
    # Получаем текстовые части ссылки
    # ------------------------------------------------

    parts = []

    for element in a.find_all(
        ["h1", "h2", "h3", "h4", "h5", "p", "span"],
        recursive=True
    ):

        text = element.get_text(
            " ",
            strip=True
        )

        text = " ".join(
            text.split()
        )

        if not text:
            continue

        if text not in parts:
            parts.append(text)


    if not parts:

        text = a.get_text(
            " ",
            strip=True
        )

        text = " ".join(
            text.split()
        )

        if text:
            parts = [text]


    if not parts:
        continue


    # ------------------------------------------------
    # Определяем заголовок
    # ------------------------------------------------

    title = ""

    heading_candidates = []

    for element in a.find_all(
        ["h1", "h2", "h3", "h4", "h5"]
    ):

        text = element.get_text(
            " ",
            strip=True
        )

        text = " ".join(
            text.split()
        )

        if len(text) >= 15:
            heading_candidates.append(text)


    if heading_candidates:

        title = max(
            heading_candidates,
            key=len
        )


    # ------------------------------------------------
    # Запасной вариант
    # ------------------------------------------------

    if not title:

        candidates = [
            p for p in parts
            if len(p) >= 20
        ]

        if candidates:
            title = max(
                candidates,
                key=len
            )


    if not title:
        continue


    # ------------------------------------------------
    # Определяем описание
    # ------------------------------------------------

    description = ""

    paragraph_candidates = []

    for p in a.find_all("p"):

        text = p.get_text(
            " ",
            strip=True
        )

        text = " ".join(
            text.split()
        )

        if len(text) >= 30:
            paragraph_candidates.append(text)


    if paragraph_candidates:

        description = max(
            paragraph_candidates,
            key=len
        )


    if not description:

        for part in parts:

            if part == title:
                continue

            if len(part) < 40:
                continue

            description = part
            break


    if len(description) > 600:

        description = (
            description[:600]
            .rsplit(" ", 1)[0]
            + "..."
        )


    # ------------------------------------------------
    # Исключаем служебные разделы
    # ------------------------------------------------

    bad_titles = {
        "Stuttgart",
        "Baden-Württemberg",
        "Politik",
        "Wirtschaft",
        "Sport",
        "Kultur",
        "Panorama",
        "Unterhaltung",
        "Wissen",
        "Reise",
        "Alle Themen"
    }

    if title in bad_titles:
        continue


    # ------------------------------------------------
    # RSS item
    # ------------------------------------------------

    pub_date = time.strftime(
        "%a, %d %b %Y %H:%M:%S +0000",
        time.gmtime()
    )

    items.append(
        f"""
<item>
  <title>{escape(title)}</title>
  <link>{escape(link)}</link>
  <description><![CDATA[{description}]]></description>
  <guid isPermaLink="true">{escape(link)}</guid>
  <pubDate>{pub_date}</pubDate>
</item>"""
    )

    print(
        "ADDED:",
        title
    )

    if len(items) >= MAX_ITEMS:
        break


# --------------------------------------------------
# Создаём RSS
# --------------------------------------------------

rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Stuttgarter Zeitung – Wirtschaft</title>
    <link>{escape(SOURCE_URL)}</link>
    <description>Aktuelle Wirtschaftsnachrichten – Stuttgarter Zeitung</description>
    <language>de-DE</language>
    {''.join(items)}
  </channel>
</rss>
'''


# --------------------------------------------------
# Сохраняем
# --------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(rss)


print(
    f"DONE - RSS contains {len(items)} articles"
)
