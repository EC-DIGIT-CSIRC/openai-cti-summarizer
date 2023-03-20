import re


import uvicorn

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import BaseSettings

import openai
import openai.error

from app.misc import LORE_IPSUM

model = "gpt-3.5-turbo",        #  for chat...
model = 'text-davinci-003'      # the default GPT-3 model (text completion)
model = 'gpt-4'
# model = 'gpt-4-32k'           # 32k token access should come later


class Settings(BaseSettings):
    OPENAI_API_KEY: str = 'OPENAI_API_KEY'
    DRY_RUN: bool = True

    class Config:
        env_file = '.env'

settings = Settings()
openai.api_key = settings.OPENAI_API_KEY


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
async def index(request: Request,  text : str= Form(...), API_KEY: str = settings.OPENAI_API_KEY):
    
    if API_KEY:
        openai.api_key = API_KEY
    else:
        openai.api_key = settings.OPENAI_API_KEY
    try:
        if settings.DRY_RUN:
            response = "This is a sample response, we are in dry-run mode. We don't want to waste money for querying the API." + \
                LORE_IPSUM
            print(response)
        else:
            messages=[
                {"role": "system", "content": "You are a Cyber Threat Intelligence Analyst and need to summarise a report for upper management"},
                {"role": "user", "content": text}
            ]

            response = openai.ChatCompletion.create(          # this is used for the gpt-3.5-turbo as well as GPT-4 model...
                model=model,
                # prompt=generate_prompt(text),     # this is the way we did it in GPT-3
                messages = messages,
                temperature=0.7,
                max_tokens=500,
                n = 1,
            )
        if settings.DRY_RUN:
            result = response
        else:
            result = response.choices[0].message.content       # type: ignore
        print(f"response = '{response}'")
    except openai.error.OpenAIError as e: 
        #Handle API error here, e.g. retry or log
        print(f"OpenAI API returned an API Error: {e}")
        return templates.TemplateResponse("index.html", { "request": request, "result": e, "success": False}, status_code=400)
    except Exception as e:
        print(f"Unknown error! Error = '{str(e)}'")
        return templates.TemplateResponse("index.html", { "request": request, "result": str(e), "success": False}, status_code=400)
        # raise HTTPException(status_code = 500, detail=str(e))
    return templates.TemplateResponse("index.html", {"request": request, "result": result, "success": True, "api_key": API_KEY })


def generate_prompt(text: str):
    prompt: str = f"""Summarize the following Cyber Threat Intelligence report for high level IT managers. Focus on the facts and geopolitics which might be relevant for the European Union, the EU Commission or other EU Institutions, Bodies and agencies: '''{text}'''"""
    text = prompt + text
    text = re.sub('\n', ' ', text)
    text = re.sub('\s+', ' ', text)
    return text

if __name__ == "__main__":
    uvicorn.run('main:app', host="localhost", port=9999, reload=True)
