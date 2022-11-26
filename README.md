# OpenAI and FastAPI - Python example app

This is an example pet name generator app used in the OpenAI API [quickstart tutorial](https://beta.openai.com/docs/quickstart). It uses the [FastAPI](https://fastapi.tiangolo.com/) web framework. 

## Setup

1. If you don’t have Python installed, [install it from here](https://www.python.org/downloads/)

2. Clone this repository

3. Navigate into the project directory

   ```bash
   $ cd openai-quickstart-fastapi
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

8. Run the app

   ```bash
   $ python app.py
   ```
   
   ![demo](https://user-images.githubusercontent.com/59533593/173504130-6b36bad6-267a-45b2-96b9-14abe9493ad1.gif)
   
You should now be able to access the app at [http://localhost:5001](http://localhost:5001)! 

This repogitory is based on the Flask code at [openai-quickstart-python](https://github.com/openai/openai-quickstart-python). For the full context behind Flask app, check out the [Flask tutorial](https://beta.openai.com/docs/quickstart).

## Reference

- [openai/openai-quickstart-python](https://github.com/openai/openai-quickstart-python)


