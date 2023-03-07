import re


import uvicorn

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import BaseSettings

import openai

from misc import LORE_IPSUM


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
async def index(request: Request, text : str= Form(...)):
    try:
        if settings.DRY_RUN:
            response = "This is a sample response, we are in dry-run mode. We don't want to waste money for querying the API." + \
                LORE_IPSUM
            print(response)
        else:
            # response = openai.ChatCompletion.create(          # this is used for the gpt-3.5-turbo model...
            response = openai.Completion.create(
                # model="text-davinci-002",
                model="text-davinci-003",
                # model="gpt-3.5-turbo",      #  for chat...
                prompt=generate_prompt(text),
                temperature=0.1,
                max_tokens=2000,
            )
        if settings.DRY_RUN:
            result = response
        else:
            result = response.choices[0].text       # type: ignore
        print(f"response = '{response}'")
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))
    return templates.TemplateResponse("index.html", {"request": request, "result": result})


def generate_prompt(text: str):
    prompt: str = f"""Summarize the following Cyber Threat Intelligence report for high level IT managers. Focus on the facts and geopolitics which might be relevant for the European Union: '''{text}''' """
    text = prompt + text
    text = re.sub('\n', ' ', text)
    text = re.sub('\s+', ' ', text)
    return text

if __name__ == "__main__":
    uvicorn.run('app:app', host="localhost", port=5001, reload=True)
