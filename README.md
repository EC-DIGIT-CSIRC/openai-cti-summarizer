# OpenAI and FastAPI - Text summarization 

This code is losely based on [Oikosohn's](https://github.com/oikosohn/openai-quickstart-fastapi) openai quickstart fastapi repo, which in turn was based on [openai-quickstart-python](https://github.com/openai/openai-quickstart-python).


It uses the OpenAI API [quickstart tutorial](https://beta.openai.com/docs/quickstart) and the [FastAPI](https://fastapi.tiangolo.com/) web framework. 

With prompt engineering, we ask openai's gpt-3 model to summarize a CTI text for management.



## Setup

1. If you don’t have Python installed, [install it from here](https://www.python.org/downloads/)

2. Clone this repository

3. Navigate into the project directory

   ```bash
   $ cd openai-cti-summarizer
   ```

4. Create a new virtual environment

   ```bash
   # Linux
   $ python -m venv venv
   $ . venv/bin/activate
   ```

   ```shell
   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

5. Install the requirements

   ```bash
   $ pip install -r requirements.txt
   ```

6. Make a copy of the example environment variables file

   ```bash
   # Linux
   $ cp .env.example .env
   ```

   ```shell
   # Windows
   xcopy .env.example .env
   ```

7. Add your [API key](https://beta.openai.com/account/api-keys) to the newly created `.env` file
   *Note*: when coding, you might want to not send a request to openai for every page reload. In that case, set `DRY_RUN=1` in `.env`.

8. Run the app

   ```bash
   $ uvicorn --reload --port=5001 --host=0.0.0.0 app:app
   ```
   
   
You should now be able to access the app at [http://localhost:5001](http://localhost:5001)! 


## Reference

- [openai/openai-quickstart-python](https://github.com/openai/openai-quickstart-python)
- [Oikosohn's fastapi openai demo](https://github.com/oikosohn/openai-quickstart-fastapi)

