import openai
import openai.error
from typing import Tuple


class Summarizer:
    def __init__(self, API_KEY: str, model: str, max_tokens: int, system_prompt: str = "", go_azure: bool = False):
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = "You are a Cyber Threat Intelligence Analyst and need to summarise a report for upper management. The report shall be nicely formatted with two sections: one Executive Summary section and one 'TTPs and IoCs' section. The second section shall list all IP addresses, domains, URLs, tools and hashes (sha-1, sha256, md5, etc.) which can be found in the report. Nicely format the report as markdown. Use newlines between markdown headings."
        self.API_KEY = API_KEY
        self.model = model
        self.max_tokens = max_tokens
        self.go_azure = go_azure
        if self.go_azure:
            openai.api_type = "azure"
            openai.api_base = "https://devmartiopenai.openai.azure.com/"
            openai.api_version = "2023-05-15"
        openai.api_key = self.API_KEY

    def summarize(self, text: str, system_prompt: str = "") -> Tuple[str, str]:
        """Send <text> to openAI and get a summary back.
        Returns a tuple: error, message. Note that either error or message may be None.
        """
        if not system_prompt:
            system_prompt = self.system_prompt
        messages = [
            {"role": "system", "content": system_prompt},      # single shot
            {"role": "user", "content": text}
        ]

        # XXX FIXME: work with chunks

        try:
            if self.go_azure:
                response = openai.ChatCompletion.create(
                    engine="openai-cti-summarizer-deployment-1",
                    messages=messages,
                    temperature=0.7,
                    top_p=0.95,
                    stop=None,
                    max_tokens=self.max_tokens,     # TODO: Make sure this actually means, summarize in X token
                    n=1,
                )
            else:       # go directly via OpenAI's API
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    top_p=0.95,
                    stop=None,
                    max_tokens=self.max_tokens,
                    n=1,
                )
            result = response.choices[0].message.content
            error = None            # Or move the error handling back to main.py, not sure
        except openai.error.OpenAIError as e:
            result = None
            error = f"OpenAI API returned an API Error: {str(e)}"
        except Exception as e:
            result = None
            error = f"Unknown error! Error = '{str(e)}'"

        return result, error        # type: ignore
