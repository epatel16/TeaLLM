import openai
from getpass import getpass

class Bot:
    
    DEFAULT_SETTINGS = {
        'model' : 'gpt-3.5-turbo',
        'temperature' : 0,
        'max_tokens' : 100,
        'top_p' : 1,
        'frequency_penalty' : 0,
        'presence_penalty' : 0.0
    }
    
    def __init__(self, api_key, **client_kwargs):
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        self.client_kwargs = client_kwargs
        if self.client_kwargs is None:
            self.client_kwargs = {}
        for param in self.DEFAULT_SETTINGS:
            if not (param in self.client_kwargs):
                self.client_kwargs[param] = self.DEFAULT_SETTINGS[param]
    
    @classmethod
    def get_query(_, role, content):
        return {'role' : role, 'content' : content}
    
    def __call__(self, prompt, stop=["\n"]):
        response = self.client.chat.completions.create(
            messages=[Bot.get_query(role='user', content=prompt)],
            stop=stop,
            **self.client_kwargs
        )
        return response.choices[0].message.content
    
if __name__ == '__main__':
    bot = Bot(api_key=getpass('Enter your OpenAI key: '))
    reply = bot("Hello! What's your name?", stop=None)
    print(reply)