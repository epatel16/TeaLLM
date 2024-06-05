from openai import OpenAI
from scraper import *


class WikiBot:
    
    def __init__(self, prompt):
        self.prompt = prompt
        self.messages = []
        self.messages.append(self.get_query('system', prompt))
    
    def get_wikipedia(self, topic):
        response = httpx.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json"
        })

        search_results = response.json().get("query", {}).get("search", [])
        if not search_results:
            return "No results found."

        first_result_title = search_results[0]["title"]
        page_url = f"https://en.wikipedia.org/wiki/{first_result_title.replace(' ', '_')}"
        return self.scrape_wikipedia_article(page_url)

    def scrape_wikipedia_article(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to load page {url}")

        soup = BeautifulSoup(response.content, 'html.parser')

        content_div = soup.find(id='mw-content-text')
        if not content_div:
            raise Exception("Failed to find main content of the article")

        paragraphs = content_div.find_all('p')
        article_text = "".join([p.text for p in paragraphs if p.get_text().strip() != ""])
        return article_text
    
    def get_query(self, role, message):
        return {'role': role, 'content': message}
        
    def __call__(self, topic):
        wiki_article = self.get_wikipedia(topic)
        if len(self.messages) < 2:
            self.messages.append(self.get_query(wiki_article))
        else:
            self.messages[2] = self.get_query(wiki_article)
            
        result = self.execute()
        return result
    
    def execute(self):
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.messages
        )
        return response.choices[0].message.content
    
class ChatBot:
    def __init__(self, system=""):
        self.system = system
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.messages
        )

        return response.choices[0].message.content