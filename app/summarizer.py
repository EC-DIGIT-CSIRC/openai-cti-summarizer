import openai
import openai.error
from typing import Tuple

class Summarizer:
    def __init__(self, API_KEY: str, model: str, max_tokens: int):
        self.base_prompt = "You are a Cyber Threat Intelligence Analyst and need to summarise a report for upper management. The report shall be nicely formatted with two sections: one Executive Summary section and one 'TTPs and IoCs' section. The second section shall list all IP addresses, domains, URLs, tools and hashes (sha-1, sha256, md5, etc.) which can be found in the report. Nicely format the report as markdown. Use newlines between markdown headings."
        self.API_KEY = API_KEY
        self.model = model
        self.max_tokens = max_tokens
        openai.api_key = self.API_KEY

    def summarize(self, text: str) -> Tuple[str, str]:
        messages = [
            {"role": "system", "content": self.base_prompt},
            {"role": "user", "content": text}
        ]

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=self.max_tokens, # TODO: Make sure this actually means, summarize in X token
                n=1,
            )
            result = response.choices[0].message.content
            error = None    # Or move the error handling back to main.py, not sure
        except openai.error.OpenAIError as e:
            result = None
            error = f"OpenAI API returned an API Error: {e}"
        except Exception as e:
            result = None
            error = f"Unknown error! Error = '{str(e)}'"

        return result, error # type: ignore
