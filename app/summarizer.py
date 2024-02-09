import os
from typing import Tuple

import openai
from openai import AzureOpenAI

from settings import log

# first get the env parametting
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())      # read local .env file


class Summarizer:
    """Wrapper to summarize texts via OpenAI or MS Azure's OpenAI."""

    client: openai._base_client.BaseClient

    def __init__(self, model: str, max_tokens: int, system_prompt: str = "", go_azure: bool = False, output_json: bool = False):
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = "You are a Cyber Threat Intelligence Analyst and need to summarise a report for upper management. The report shall be nicely formatted with two sections: one Executive Summary section and one 'TTPs and IoCs' section. The second section shall list all IP addresses, domains, URLs, tools and hashes (sha-1, sha256, md5, etc.) which can be found in the report. Nicely format the report as markdown. Use newlines between markdown headings."
        self.model = model
        self.max_tokens = max_tokens
        self.go_azure = go_azure
        self.output_json = output_json

        if self.go_azure:
            api_version = os.environ['OPENAI_API_VERSION']
            azure_endpoint = os.environ['OPENAI_API_BASE']
            azure_deployment = os.environ['ENGINE']
            api_key = os.environ['AZURE_OPENAI_API_KEY']
            log.debug(f"""
                {api_version=},
                {azure_endpoint=},
                {azure_deployment=},
                {api_key=}
            """)
            self.client = AzureOpenAI(api_version=os.environ['OPENAI_API_VERSION'],
                                      azure_endpoint=os.environ['OPENAI_API_BASE'],
                                      azure_deployment=os.environ['ENGINE'],
                                      api_key=os.environ['AZURE_OPENAI_API_KEY'])

            # TODO: The 'openai.api_base' option isn't read in the client API. You will need to pass it when you instantiate the client, e.g. 'OpenAI(api_base=os.environ['OPENAI_API_BASE'])'
            # openai.api_base = os.environ['OPENAI_API_BASE']             # Your Azure OpenAI resource's endpoint value.
            # "2023-05-15"

            """
            openai.api_type = os.environ['OPENAI_API_TYPE']
            openai.api_base = os.environ['OPENAI_API_BASE']             # "https://devmartiopenai.openai.azure.com/"
            openai.api_version = os.environ['OPENAI_API_VERSION']       # "2023-05-15"
            """
            log.info(f"Using Azure client {self.client._version}")
        else:
            self.client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])

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

        try:
            if self.go_azure:
                log.info("Using MS AZURE!")
                response = self.client.chat.completions.create(model=os.environ['ENGINE'],
                                                               messages=messages,
                                                               temperature=0.3,
                                                               top_p=0.95,
                                                               stop=None,
                                                               max_tokens=self.max_tokens,
                                                               n=1)
            else:       # go directly via OpenAI's API
                log.info("Using OpenAI directly!")
                if self.output_json:
                    response_format = {"type": "json_object"}
                else:
                    response_format = None
                response = self.client.chat.completions.create(model=self.model,
                                                               messages=messages,
                                                               temperature=0.3,
                                                               top_p=0.95,
                                                               stop=None,
                                                               max_tokens=self.max_tokens,
                                                               response_format=response_format,
                                                               n=1)
                
            log.debug(f"Full Response (OpenAI): {response}")
            log.debug(f"response.choices[0].text: {response.choices[0].message}")
            log.debug(response.model_dump_json(indent=2))
            result = response.choices[0].message.content
            error = None            # Or move the error handling back to main.py, not sure
        except openai.APIConnectionError as e:
            result = None
            error = f"The server could not be reached. Reason {e.__cause__}"
            log.error(error)
        except openai.RateLimitError as e:
            result = None
            error = f"A 429 status code was received; we should back off a bit. {str(e)}"
            log.error(error)
        except openai.APIStatusError as e:
            result = None
            error = f"Another non-200-range status code was received. Status code: {e.status_code}. \n\nResponse: {e.message}"
            log.error(error)
        except Exception as e:
            result = None
            error = f"Unknown error! Error = '{str(e)}'"
            log.error(error)

        return result, error        # type: ignore
