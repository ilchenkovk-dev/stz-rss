import requests
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape
from urllib.parse import urljoin
import time
import traceback


# --------------------------------------------------
# Настройки
# --------------------------------------------------

SOURCE_URL = "https://www.stuttgarter-zeitung.de/lokales/stuttgart/"
OUTPUT_FILE = "stuttgart.xml"

MAX_ITEMS = 30

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}


# --------------------------------------------------
# Получаем страницу Stuttgart
# --------------------------------------------------

try:
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

except Exception:
    print("FETCH MAIN PAGE FAILED")
    traceback.print_exc()
    exit(1)


# --------------------------------------------------
# Ищем ссылки на статьи
# --------------------------------------------------

seen = set()
articles = []

for a in soup.find_all("a", href=True):

    href = a.get("href")
    link = urljoin(SOURCE_URL, href)

    # Только ссылки Stuttgarter Zeitung
    if not link.startswith(
        "https://www.stuttgarter-zeitung.de/"
    ):
        continue

    # Не берём сам раздел Stuttgart
    if link.rstrip("/") == SOURCE_URL.rstrip("/"):
        continue

    # Не обрабатываем одну и ту же ссылку несколько раз
    if link in seen:
        continue

    seen.add(link)

    # Текст ссылки нам здесь не нужен.
    # Настоящий заголовок возьмём со страницы статьи.

    articles.append(link)

    if len(articles) >= MAX_ITEMS:
        break


print(
    f"Found {len(articles)} possible article links"
)


# --------------------------------------------------
# Получаем содержимое каждой статьи
# --------------------------------------------------

items = []

for href in articles:

    try:

        print("Processing:", href)

        art_res = requests.get(
            href,
            headers=headers,
            timeout=15
        )

        art_res.raise_for_status()

        art_soup = BeautifulSoup(
            art_res.text,
            "html.parser"
        )

        # ------------------------------------------
        # Ищем настоящий заголовок статьи
        # ------------------------------------------

        article_title = art_soup.find("h1")

        if not article_title:
            print("NO H1:", href)
            continue

        title = article_title.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        # ------------------------------------------
        # Удаляем ненужные элементы
        # ------------------------------------------

        for trash in art_soup.find_all(
            [
                "nav",
                "header",
                "footer",
                "script",
                "style",
                "aside",
                "form"
            ]
        ):
            trash.decompose()

        # ------------------------------------------
        # Ищем текст статьи
        # ------------------------------------------

        paragraphs = []

        # Вариант 1:
        # ищем контейнер вокруг H1
        parent = article_title.find_parent()

        if parent:

            for p in parent.find_all("p"):

                text = p.get_text(
                    " ",
                    strip=True
                )

                if len(text) > 30:
                    paragraphs.append(text)

        # ------------------------------------------
        # Вариант 2:
        # если текста около H1 не нашли,
        # ищем типичные контейнеры статьи
        # ------------------------------------------

        if not paragraphs:

            selectors = [
                "article",
                '[class*="article"]',
                '[class*="content"]',
                '[class*="text"]',
                "main"
            ]

            for selector in selectors:

                content = art_soup.select_one(
                    selector
                )

                if not content:
                    continue

                for p in content.find_all("p"):

                    text = p.get_text(
                        " ",
                        strip=True
                    )

                    if len(text) > 30:
                        paragraphs.append(text)

                if paragraphs:
                    break

        # ------------------------------------------
        # Убираем дубли абзацев
        # ------------------------------------------

        clean_paragraphs = []

        for text in paragraphs:

            if text not in clean_paragraphs:
                clean_paragraphs.append(text)

        # ------------------------------------------
        # Формируем описание
        # ------------------------------------------

        desc = " ".join(
            clean_paragraphs
        )

        desc = desc.strip()

        if len(desc) > 500:
            desc = desc[:500].rsplit(
                " ",
                1
            )[0] + "..."

        if not desc:
            print(
                "NO ARTICLE TEXT:",
                href
            )
            continue

        # ------------------------------------------
        # Дата
        # ------------------------------------------

        pub_date = time.strftime(
            "%a, %d %b %Y %H:%M:%S +0000",
            time.gmtime()
        )

        # ------------------------------------------
        # RSS item
        # ------------------------------------------

        items.append(
            f"""
<item>
  <title>{escape(title)}</title>
  <link>{escape(href)}</link>
  <description><![CDATA[{desc}]]></description>
  <guid isPermaLink="true">{escape(href)}</guid>
  <pubDate>{pub_date}</pubDate>
</item>"""
        )

        print(
            "OK:",
            title
        )

    except Exception as e:

        print(
            "ARTICLE FETCH FAILED:",
            href
        )

        print(
            repr(e)
        )

        continue


# --------------------------------------------------
# Создаём RSS
# --------------------------------------------------

rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Stuttgarter Zeitung – Stuttgart</title>
    <link>{escape(SOURCE_URL)}</link>
    <description>Aktuelle Nachrichten aus Stuttgart – Stuttgarter Zeitung</description>
    <language>de-DE</language>
    {''.join(items)}
  </channel>
</rss>
'''


# --------------------------------------------------
# Сохраняем RSS
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
