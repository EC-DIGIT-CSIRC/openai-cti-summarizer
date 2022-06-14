import openai

import uvicorn

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from pydantic import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str = 'OPENAI_API_KEY'

    class Config:
        env_file = '.env'

settings = Settings()
openai.api_key = settings.OPENAI_API_KEY


app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
def index(request: Request, animal: str= Form(...)):
    response = openai.Completion.create(
        model="text-davinci-002",
        prompt=generate_prompt(animal),
        temperature=0.6,
    )
    result = response.choices[0].text
    return templates.TemplateResponse("index.html", {"request": request, "result": result})


def generate_prompt(animal):
    return """Suggest three names for an animal that is a superhero.

Animal: Cat
Names: Captain Sharpclaw, Agent Fluffball, The Incredible Feline
Animal: Dog
Names: Ruff the Protector, Wonder Canine, Sir Barks-a-Lot
Animal: {}
Names:""".format(
        animal.capitalize()
    )

if __name__ == "__main__":
    uvicorn.run('app:app', host="localhost", port=5001, reload=True)