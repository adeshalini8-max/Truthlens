
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from urllib.parse import urlparse


def search_web(query: str):
    query = query.strip()

    if not query:
        return []

    results = []
    seen_urls = set()

    # Search for relevant web results, not only exact phrases.
    queries = [
        query,
        f"{query} fact check",
        f"{query} latest news",
    ]

    try:
        with DDGS() as ddgs:
            for search_query in queries:
                try:
                    items = ddgs.text(
                        search_query,
                        max_results=5
                    )

                    for item in items:
                        url = item.get("href") or item.get("url") or ""

                        if not url or url in seen_urls:
                            continue

                        seen_urls.add(url)
                        domain = urlparse(url).netloc

                        results.append({
                            "title": item.get("title", ""),
                            "url": url,
                            "snippet": item.get("body", ""),
                            "source": domain,
                            "published": "",
                            "relevance": 0
                        })

                        if len(results) >= 10:
                            return results

                except Exception as e:
                    print("SEARCH QUERY ERROR:", e)

    except Exception as e:
        print("WEB SEARCH ERROR:", e)

    return results
