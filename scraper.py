import httpx, requests, re
from bs4 import BeautifulSoup
import os, openai
# TODO: this is probably really bad at reading tables 
class WikiScraper:
    
    def __init__(self):
        self.response = None
        self.soup = None
        self.full_text = None
        self.big_headers = None
        self.title = None
        self.page_url = None
        self.topic = None
        self.paragraphs = None
        self.steps = 0
        self.obs = ("Interact with Wikipedia using search[], lookup[], and finish[].\n")
        self.loaded = False
    
    def set_topic(self, topic):
        self.loaded = False
        self.topic = topic
        try:
            self.find_article()
            self.scrape_article()
            self.loaded = True
        except Exception as e:
            print(e)
            print('Unknown error occured during finding and scraping...')
        
    def get_subsection(self, header, stop=None):
        """Gets the subection under a header for the article"""
        bs4_header = None
        for h in self.bs4_article_headers:
            if header in h.text:
                bs4_header = h
                break
        ret = []
        if stop is None: stop == bs4_header.name
        for sibling in bs4_header.next_siblings:
            if sibling.name == 'p':
                ret.append(sibling.text)
            elif sibling.name == bs4_header.name:
                break
        return '\n'.join(self.paragraphs_text[:min(3, len(self.paragraphs_text))] + ret)
    
    def get_headers(self, sep='\n'):
        """A string seperated by sep (defualt newline) of the headers in the
        article"""
        return sep.join(self.str_article_headers)
        
    def find_article(self):
        """Identify the wikipedia article most related to self.topic"""
        self.response = httpx.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query",
            "list": "search",
            "srsearch": self.topic,
            "format": "json"
        })

        search_results = self.response.json().get("query", {}).get("search", [])
        if not search_results:
            raise Exception("No results found.")

        self.title = search_results[0]["title"]
        self.other_results = [result['title'] for result in search_results[1:]]
        self.page_url = f"https://en.wikipedia.org/wiki/{self.title.replace(' ', '_')}"
    
    def scrape_article(self):
        """Scrape the wikipedia article at self.page_url"""
        self.response = requests.get(self.page_url)
        if self.response.status_code != 200:
            raise Exception(f"Failed to load page {self.page_url}")

        self.soup = BeautifulSoup(self.response.content, 'html.parser')

        content_div = self.soup.find(id='mw-content-text')
        if not content_div:
            raise Exception("Failed to find main content of the article")

        self.paragraphs = content_div.find_all('p')
        self.paragraphs_text = [p.text for p in self.paragraphs if p.get_text().strip() != ""]
        self.full_text = ''.join(self.paragraphs_text)
        self.bs4_article_headers = list(content_div.find_all('h3')) \
                                 + list(content_div.find_all('h2'))
        self.str_article_headers = []
        for header in self.bs4_article_headers:
            text = header.text
            text = text[:-6] if '[edit]' in text[-7:] else text
            self.str_article_headers.append(text)
        
        self.bs4_links = content_div.find_all('a')
        self.links = []
        self.link2url = {}
        for bs4_link in self.bs4_links:
            if 'title' in bs4_link.attrs:
                self.links.append(bs4_link.attrs['title'])
                self.link2url[bs4_link.attrs['title']] = bs4_link.attrs['href']
        
    def get_links(self):
        return self.links, self.link2url
        
    def get_paragraphs_with(self, phrase):
        ret = []
        for p in self.paragraphs:
            if re.search(phrase, p.text, re.IGNORECASE):
                ret.append(p.text)
                
        return ret
    

class WikiSearch:
    
    def __init__(self, api_key, prompt1_file='prompts/wiki_pt1.txt',
                                prompt2_file='prompts/wiki_pt2.txt',
                                crawl_file='prompts/wiki_crawl.txt'):
        self.scraper = WikiScraper()
        self.client = openai.OpenAI(api_key=api_key)
        self.instructions = {}
        with open(prompt1_file, 'r') as f:
            self.instructions['headers'] = '\n'.join(f.readlines())
        with open(prompt2_file, 'r') as f:
            self.instructions['paragraphs'] = '\n'.join(f.readlines())
        with open(crawl_file, 'r') as f:
            self.instructions['crawl'] = '\n'.join(f.readlines())
        self.obs = ("Interact with Wikipedia using search, crawl, similar, and finish[].\n")
        self.messages = []
        self.question = None
        self.steps = 0
        self.answer = None
    
    @staticmethod
    def get_query(role, message):
        return {'role': role, 'content': message}
    
    def llm(self, prompt, instruction='headers'):
        self.messages = []
        if instruction in self.instructions:
            self.messages.append(self.get_query('system', self.instructions[instruction]))
            self.messages.append(self.get_query('user', prompt))
        else:
            raise Exception(f'WikiSearch: Bad input to instruction (keyError) {instruction}')
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.messages,
            temperature=0,
            max_tokens=4096,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        self.messages.append(self.get_query('assistant', response.choices[0].message.content))
        return response.choices[0].message.content
    
    def reset(self, idx=None):
        idx # remnant of wrapping functions...can (and should) ignore
        self.messages = []
        self.steps = 0
        self.messages.append(self.get_query('system', self.instruction))
        self.answer = None
        self.obs = ("Interact with Wikipedia using search, crawl, similar, and finish[].\n")
    
    def find_similar_headers(self, selected_headers: str, real_headers: str):
        selected_headers = selected_headers.split('\n')
        ret = [header for header in selected_headers if header != '' and header in real_headers]
        return ret
        
    def search(self, topic, question, keyphrase):
        # part 1
        self.scraper.set_topic(topic)
        if not self.scraper.loaded:
            return 'No articles or similar articles were found with this topic. Please try a different topic.'
        headers = self.scraper.get_headers()
        title = self.scraper.title
        prompt = f'TITLE: {title}\nHEADERS:\n{headers}\nQUESTION: {question}'
        selected_headers = self.find_similar_headers(self.llm(prompt, instruction='headers'), headers)
        if selected_headers == []:
            return f'The article {title} was not found to have a relation to {question[:-1]}'
        
        # part 1.5
        keyparagraphs = self.scraper.get_paragraphs_with(keyphrase)
        
        # part 2
        paragraphs = [self.scraper.get_subsection(header) for header in selected_headers] + keyparagraphs
        ret = ''
        chunk = ''
        for paragraph in paragraphs:
            chunk += paragraph + '\n'
            if len(chunk) > 10_000:
                prompt = f'QUESTION:\n{question}\nTEXT:\n{chunk}'
                ret += self.llm(prompt, instruction='paragraphs') + ' '
                chunk = ''
        if chunk != '':
            prompt = f'QUESTION:\n{question}\nTEXT:\n{chunk}'
            ret += self.llm(prompt, instruction='paragraphs')

        return ret
        
    def crawl(self, question):
        if not self.scraper.loaded:
            return 'No articles or similar articles were found. Please try a different topic.'
        names, _ = self.scraper.get_links()
        names = names[0:min(len(names), 300)]
        title = self.scraper.title
        prompt = f'TITLE: {title}\nHEADERS:\n{names}\nQUESTION: {question}'
        selected_names = self.find_similar_headers(self.llm(prompt, instruction='crawl'), names)
        if selected_names == []:
            return f'The article {title} was not found to have links with a relation to {question}'
        
        return ', '.join(selected_names)
    
    def similar(self):
        if not self.scraper.loaded:
            return 'No articles or similar articles were found with this topic. Please try a different topic.'
        return ', '.join(self.scraper.other_results)
        
    def finish(self, answer):
        return answer
        
    def _get_info(self):
        return {"steps": self.steps, "answer": self.answer}
        
    def reset(self, seed=None, return_info=False, options=None):
        self.steps = 0
        self.scraper = WikiScraper()
        self.answer = None
        self.obs = ("Interact with Wikipedia using search[], lookup[], and finish[].\n")
        info = self._get_info()
        return (self.obs, info) if return_info else self.obs
    
    def verify_arguments(self, request, args, num_expected):
        if len(args) != num_expected: 
            pass #raise Exception(f'Search: Invalid arguments {args} given request {request}')
        return len(args) == num_expected
        
    # search | topic | question
    def step(self, request):
        reward = 0
        done = False
        request = request.strip().split('|')
        action, args = request[0], request[1:]
        if 'search' in action:
            success = self.verify_arguments(request, args, num_expected=3)
            if not success:
                self.obs = 'Invalid input. Please try again with correct syntax.'
            else:
                topic, question, keyphrase = args
                self.obs = self.search(topic, question, keyphrase)
        elif 'crawl' in action:
            success = self.verify_arguments(request, args, num_expected=1)
            if not success:
                self.obs = 'Invalid input. Please try again with correct syntax.'
            else:
                question = args
                self.obs = self.crawl(question)
        elif 'similar' in action:
            success = self.verify_arguments(request, args, num_expected=0)
            if not success:
                self.obs = 'Invalid input. Please try again with correct syntax.'
            else:
                self.verify_arguments(request, args, num_expected=0)
                self.obs = self.similar()
        elif 'finish' in action:
            success = self.verify_arguments(request, args, num_expected=1)
            if not success:
                self.obs = 'Invalid input. Please try again with correct syntax.'
            else:
                self.answer = args[0]
                done = True
                self.obs = self.finish(self.answer)  
        else:
            raise Exception(f'WikiSearch: Unknown action {action} requested via request {request}')
        
        self.steps += 1
        return self.obs, reward, done, self._get_info()
        
if __name__ == '__main__':
    # scraper = WikiScraper()
    # scraper.set_topic('Members of Winner')
    # print(scraper.page_url)
    # print(scraper.other_results)
    # print(scraper.get_headers())
    # print('-' * 20)
    # print(scraper.get_subsection('Skeleton')) # <-- using headers can be potentially better
    # print('-' * 20)
    # print(scraper.get_paragraphs_with('skEleton'))
    
    # scraper = WikiScraper()
    # scraper.set_topic('Airplane')
    # print(scraper.page_url)
    # print(scraper.get_headers())
    # print(scraper.get_subsection('Development of jet aircraft'))
    api_key = None
    if not ('OPENAI_API_KEY' in os.environ):
        api_key = input("Enter your OpenAI API key: ")
        os.environ["OPENAI_API_KEY"] = api_key
    searcher = WikiSearch(api_key=api_key)
    # print(searcher.search('Airplanes', 'How do planes fly?'))
    # print(searcher.search(' airplanes ', ' how do planes fly? '))
    # print(searcher.step('crawl | airplanes | how do planes fly?'))
    # print(searcher.step('crawl|Milhouse Van Houten|Who is Milhouse named after?'))
    # print(searcher.step('crawl|2014 S/S|2014 S/S is the debut album of a South Korean boy group that was formed by who?'))
    print(searcher.step('search | Winner | who formed the South Korean boy group Winner? | formation'))
    # print(searcher.step("crawl | who are some famous bollywood actors whose name starts with H?"))
