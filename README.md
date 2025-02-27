# Building an AI Chatbot Website with Backblaze B2 + LangChain 

This app shows you how to implement a simple AI chatbot website that uses a large language model (LLM) and retrieval augmented generation (RAG) to answer questions based on a collection of PDFs stored in a private [Backblaze B2 Cloud Object Storage](https://www.backblaze.com/cloud-storage) Bucket. The app builds on the techniques introduced in the [Retrieval-Augmented Generation with Backblaze B2](https://github.com/backblaze-b2-samples/ai-rag-examples) samples. 

## Prerequisites

### Poppler

On macOS

```shell
brew install poppler
```

## Installation

Clone this repository onto your host, `cd` into the local repository directory, then use `pip install` to install dependencies:

```bash
git clone git@github.com:backblaze-b2-samples/ai-rag-app-part-1
cd ai-rag-app-part-1
pip install -r requirements.txt
```

## Configuration

Copy `.env.template` to `.env`, or set environment variables with your configuration:

```dotenv
# AWS SDK credentials and configuration
AWS_ACCESS_KEY_ID=<Backblaze Application Key ID>
AWS_SECRET_ACCESS_KEY=<Backblaze Application Key ID>
AWS_DEFAULT_REGION=<Backblaze endpoint region, e.g. us-west-004>
AWS_ENDPOINT_URL=<Backblaze bucket endpoint URL, e.g. https://s3.us-west-004.backblazeb2.com>

# App config
BUCKET_NAME=<Backblaze bucket name>
PDF_LOCATION=<Location of source PDFs within the bucket, e.g. pdfs>
VECTOR_DB_LOCATION=<Location to create vector databases within the bucket, e.g. vectordb>

# You can configure one of OpenAI, Google Gemini or DeepSeek
OPENAI_API_KEY=<Open AI API key>

GEMINI_API_KEY=<Google Gemini API key>
GOOGLE_APPLICATION_CREDENTIALS=<Location of Google service account key file>

DEEPSEEK_API_KEY=<DeepSeek API key>
```

TBD - `mysite/settings.py`

The app does not use the database, so there is no need to run `python manage.py migrate`. 

## Run the Web App

To start the development server:

```bash
python manage.py runserver
```

You may provide the runserver command with the interface and port to which the web app should bind. For example, to
listen on the standard HTTP port on all interfaces, you would use:

```bash
python manage.py runserver 0.0.0.0:80
```

## Running in Gunicorn

Django's `runserver` command starts a lightweight development server, which is not suitable for production. For 
production, you should use a [WSGI](https://wsgi.readthedocs.io/en/latest/) server such as [Gunicorn](https://gunicorn.org/).
Gunicorn is included in `requirements.txt`, so you can easily run the app with Gunicorn. From the project directory:

```shell
gunicorn --config python:config.gunicorn mysite.wsgi
```

## TBD - Running Gunicorn as a service with nginx

## Running in Docker

You can build a Docker image with the command:

```shell
docker build -t ai-rag-app .
```

You must configure the required environment variables. One way to do so is to use `docker run`'s `--env-file` option.
If you are using Google Gemini you must also provide a bind mount to a host directory containing the GCP service account
key. For example:

```shell
docker run -p 8000:8000 --env-file .env -v ./creds:/app/creds ai-rag-app
```
