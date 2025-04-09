FROM python:3.11-bullseye

# create a working directory
RUN mkdir /app
WORKDIR /app

# copy the requirements.txt file
COPY requirements.txt .

# install the dependencies
RUN pip install -r requirements.txt

# copy the main files
COPY app /app
COPY templates /templates
COPY static /static
COPY .env /
COPY VERSION.txt  /

# expose the port for the FastAPI application
EXPOSE 9999

# run the FastAPI application
CMD ["uvicorn", "main:app", "--access-log", "--reload", "--host", "0.0.0.0", "--port", "9999"]

