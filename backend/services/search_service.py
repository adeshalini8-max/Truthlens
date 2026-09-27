import requests
from bs4 import BeautifulSoup
from urllib.parse import quote


def search_web(query: str):

    query = query.strip()

    if not query:
        return []

    # Exact-phrase search
    search_query = f'"{query}"'

    url = (
        "https://news.google.com/rss/search?"
        f"q={quote(search_query)}"
        "&hl=en-IN"
        "&gl=IN"
        "&ceid=IN:en"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")

        results = []

        for item in soup.find_all("item")[:10]:

            title_element = item.find("title")
            link_element = item.find("link")
            description_element = item.find("description")
            pub_date_element = item.find("pubDate")
            source_element = item.find("source")

            title = (
                title_element.get_text(strip=True)
                if title_element
                else ""
            )

            link = (
                link_element.get_text(strip=True)
                if link_element
                else ""
            )

            description = (
                description_element.get_text()
                if description_element
                else ""
            )

            snippet = BeautifulSoup(
                description,
                "html.parser"
            ).get_text(" ", strip=True)

            published = (
                pub_date_element.get_text(strip=True)
                if pub_date_element
                else ""
            )

            source = (
                source_element.get_text(strip=True)
                if source_element
                else ""
            )

            results.append({
                "title": title,
                "url": link,
                "snippet": snippet,
                "published": published,
                "source": source
            })

        return results

    except requests.RequestException as e:

        print("SEARCH ERROR:", e)

        return []

    except Exception as e:

        print("SEARCH ERROR:", e)

        return []