import httpx, requests
from bs4 import BeautifulSoup

def wikipedia2(q):
    response = httpx.get("https://en.wikipedia.org/w/api.php", params={
        "action": "query",
        "list": "search",
        "srsearch": q,
        "format": "json"
    })

    search_results = response.json().get("query", {}).get("search", [])

    if not search_results:
        return "No results found."

    first_result_title = search_results[0]["title"]
    page_url = f"https://en.wikipedia.org/wiki/{first_result_title.replace(' ', '_')}"

    return scrape_wikipedia_article(page_url)

def scrape_wikipedia_article(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to load page {url}")

    soup = BeautifulSoup(response.content, 'html.parser')

    content_div = soup.find(id='mw-content-text')
    if not content_div:
        raise Exception("Failed to find main content of the article")

    paragraphs = content_div.find_all('p')

    article_text = "".join([p.text for p in paragraphs if p.get_text().strip() != ""])
    # [print() for p in paragraphs if p.get_text().strip() != ""]

    return article_text