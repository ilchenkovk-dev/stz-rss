import requests
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape
from urllib.parse import urljoin
import time
import traceback


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
# Загружаем страницу раздела
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
# Ищем статьи
# --------------------------------------------------

items = []
seen = set()

for a in soup.find_all("a", href=True):

    href = a.get("href")
    link = urljoin(SOURCE_URL, href)

    # Только Stuttgarter Zeitung
    if not link.startswith(
        "https://www.stuttgarter-zeitung.de/"
    ):
        continue

    # Не берём ссылки на разделы
    if link.rstrip("/") in [
        "https://www.stuttgarter-zeitung.de",
        "https://www.stuttgarter-zeitung.de/lokales",
        "https://www.stuttgarter-zeitung.de/lokales/stuttgart",
        "https://www.stuttgarter-zeitung.de/politik",
        "https://www.stuttgarter-zeitung.de/wirtschaft",
        "https://www.stuttgarter-zeitung.de/sport",
        "https://www.stuttgarter-zeitung.de/kultur",
    ]:
        continue

    # Для статьи StZ характерен URL с .html
    if not link.endswith(".html"):
        continue

    if link in seen:
        continue

    seen.add(link)

    # ------------------------------------------------
    # Содержимое ссылки
    # ------------------------------------------------

    text = a.get_text(
        " ",
        strip=True
    )

    if not text:
        continue

    # Убираем лишние пробелы
    text = " ".join(text.split())

    # ------------------------------------------------
    # Пытаемся определить заголовок
    #
    # В актуальном HTML StZ внутри ссылки могут
    # находиться несколько текстовых частей:
    #
    # надзаголовок
    # основной заголовок
    # описание
    # регион
    #
    # Поэтому отдельно ищем заголовочные элементы.
    # ------------------------------------------------

    title = ""

    for tag in a.find_all(
        ["h1", "h2", "h3", "h4", "h5"]
    ):

        candidate = tag.get_text(
            " ",
            strip=True
        )

        candidate = " ".join(
            candidate.split()
        )

        if len(candidate) >= 15:
            title = candidate
            break

    # Если заголовочного элемента нет,
    # пробуем получить title из aria-label
    if not title:

        aria = a.get("aria-label")

        if aria:
            title = " ".join(
                aria.split()
            )

    # Если ничего не нашли — пропускаем
    if not title:
        continue

    # Слишком короткие/служебные элементы
    if len(title) < 15:
        continue

    # ------------------------------------------------
    # Получаем описание
    # ------------------------------------------------

    description = ""

    # Ищем p внутри ссылки
    paragraphs = []

    for p in a.find_all("p"):

        p_text = p.get_text(
            " ",
            strip=True
        )

        p_text = " ".join(
            p_text.split()
        )

        if len(p_text) >= 30:
            paragraphs.append(p_text)

    if paragraphs:
        description = " ".join(
            paragraphs
        )

    # ------------------------------------------------
    # Если <p> нет, пробуем текстовые элементы
    # ------------------------------------------------

    if not description:

        candidates = []

        for tag in a.find_all(
            ["div", "span"]
        ):

            candidate = tag.get_text(
                " ",
                strip=True
            )

            candidate = " ".join(
                candidate.split()
            )

            if (
                len(candidate) >= 50
                and candidate != title
            ):
                candidates.append(candidate)

        if candidates:
            # Берём самый короткий подходящий текст,
            # чтобы не захватить весь блок целиком.
            candidates.sort(
                key=len
            )

            description = candidates[0]

    # ------------------------------------------------
    # Если описание не нашли,
    # пробуем открыть саму статью
    # ------------------------------------------------

    if not description:

        try:

            article_response = requests.get(
                link,
                headers=headers,
                timeout=15
            )

            article_response.raise_for_status()

            article_soup = BeautifulSoup(
                article_response.text,
                "html.parser"
            )

            article_h1 = article_soup.find("h1")

            # Удаляем ненужное
            for trash in article_soup.find_all(
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

            paragraphs = []

            if article_h1:

                parent = article_h1.find_parent()

                if parent:

                    for p in parent.find_all("p"):

                        p_text = p.get_text(
                            " ",
                            strip=True
                        )

                        if len(p_text) > 30:
                            paragraphs.append(
                                p_text
                            )

            if not paragraphs:

                for p in article_soup.find_all("p"):

                    p_text = p.get_text(
                        " ",
                        strip=True
                    )

                    if len(p_text) > 30:
                        paragraphs.append(
                            p_text
                        )

            if paragraphs:

                description = " ".join(
                    paragraphs
                )

        except Exception as e:

            print(
                "ARTICLE FETCH FAILED:",
                link,
                repr(e)
            )

    # ------------------------------------------------
    # Финальная очистка description
    # ------------------------------------------------

    description = " ".join(
        description.split()
    )

    if len(description) > 600:

        description = (
            description[:600]
            .rsplit(" ", 1)[0]
            + "..."
        )

    if not description:
        description = title

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
# RSS
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


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(rss)


print(
    f"DONE - RSS contains {len(items)} articles"
)
