# Building an AI Chatbot Website with Backblaze B2 + LangChain 

This app shows you how to implement a simple AI chatbot website that uses a large language model (LLM) and retrieval augmented generation (RAG) to answer questions based on a collection of documents, such as PDFs, stored in a private [Backblaze B2 Cloud Object Storage](https://www.backblaze.com/cloud-storage) Bucket. The app builds on the techniques introduced in the [Retrieval-Augmented Generation with Backblaze B2](https://github.com/backblaze-b2-samples/ai-rag-examples) samples.

You can ingest your own set of documents from Backblaze B2 or use a prebuilt vector store built from the Backblaze documentation. Once you have configured your vector store, you can use the app's web UI to ask questions; the app will use the vector database and LLM to generate an answer. The RAG chain implements [chat history](https://python.langchain.com/docs/concepts/chat_history/), so you can refer back to earlier questions and answers in a natural way.

The sample code uses [OpenAI GPT‑4o mini](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/), but you can easily configure an alternate model such as [Google Gemini 2.0 Flash](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2#2.0-flash), [DeepSeek V3](https://api-docs.deepseek.com/news/news1226), or run a local LLM using a technology such as [Ollama](https://ollama.com/). The web UI uses [ChatGPT](https://chatgpt.com/) as a model with some additional instrumentation - each answer includes the execution time of the RAG chain.

TODO - video

The app is written in Python and leverages the [Django web framework](https://www.djangoproject.com/),  [LangChain AI framework](https://python.langchain.com/docs/introduction/) and [LanceDB vector database](https://lancedb.github.io/lancedb/), all of which are open source. We used the the LangChain tutorials [Build a Retrieval Augmented Generation (RAG) App: Part 1](https://python.langchain.com/docs/tutorials/rag/), [Build a Local RAG Application](https://python.langchain.com/v0.2/docs/tutorials/local_rag/), and [Build a Chatbot](https://python.langchain.com/v0.2/docs/tutorials/chatbot/) as the starting point for the app.

## Contents

<!-- TOC -->
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Configuration](#configuration)
* [Upload Documents to Backblaze B2](#upload-documents-to-backblaze-b2)
* [Load Documents into the Vector Store](#load-documents-into-the-vector-store)
* [Run the Web App](#run-the-web-app)
* [Running in Gunicorn](#running-in-gunicorn)
* [Running Gunicorn as a service with nginx](#running-gunicorn-as-a-service-with-nginx)
* [Running in Docker](#running-in-docker)
* [Running a local LLM](#running-a-local-llm)
<!-- TOC -->

## Prerequisites

* [Python 3.13.1](https://www.python.org/downloads/release/python-3131/) (other recent Python versions _should_ work) and `pip`.
* A Backblaze account - [sign up here](https://www.backblaze.com/b2/sign-up.html?referrer=nopref).
* An OpenAI account - [sign up here](https://platform.openai.com/signup) - or [configure access to an alternate LLM](#django-configuration).

## Installation

Clone this repository onto your host, `cd` into the local repository directory, then use `pip install` to install dependencies:

```console
git clone git@github.com:backblaze-b2-samples/ai-rag-app
cd ai-rag-app
pip install -r requirements.txt
```

## Configuration

### API Credentials

For security, API credentials and associated configuration are accessed via environment variables. You can use a `.env`
file or set environment variables via any method of your choice.

To use a `.env` file, copy `.env.template` to `.env` and edit it with your API credentials and associated settings.

```dotenv
# Backblaze B2 credentials for use by AWS SDKs
AWS_ACCESS_KEY_ID=<Backblaze Application Key ID>
AWS_SECRET_ACCESS_KEY=<Backblaze Application Key ID>
AWS_DEFAULT_REGION=<Backblaze endpoint region, e.g. us-west-004>
AWS_ENDPOINT_URL=<Backblaze bucket endpoint URL, e.g. https://s3.us-west-004.backblazeb2.com>

OPENAI_API_KEY=<Open AI API key>
```

As an alternative to the four `AWS_` variables shown above, you can set `AWS_PROFILE` to reference a named profile or 
the `default` profile defined in the [shared AWS configuration files](https://docs.aws.amazon.com/sdkref/latest/guide/file-format.html):  

```dotenv
AWS_PROFILE=<A profile name or default to use the default profile>

OPENAI_API_KEY=<Open AI API key>
```

If you wish to access a vector database containing the Backblaze documentation, you can use the following read-only 
credentials to do so:

```dotenv
# Read-only credentials for accessing the Backblaze documentation vector store
AWS_ACCESS_KEY_ID=0045f0571db506a000000001a
AWS_SECRET_ACCESS_KEY=K004xV4KpvEGEwH+475+kvCojpKHhlY
AWS_DEFAULT_REGION=us-west-004
AWS_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

Note that you must still supply your own API key for OpenAI or an alternate online AI service, or configure a local LLM (see below). 

### Django Configuration

Since the app does not need the database, some of the configuration usually found in [`mysite/settings.py`](mysite/settings.py)
has been removed, and there is no need to run `python manage.py migrate` or `python manage.py createsuperuser`.

Towards the bottom of `mysite/settings.py`, you will see the configuration for the LLM and vector store embeddings. The `RAG` 
class, in `ai_rag_app/rag.py`, uses these values to create instances of the API wrapper objects. Note that the locations in the
`COLLECTION` configuration in the sample code point to the Backblaze documentation PDFs and vector store. You can use them with the read-only credentials above or change them to match your environment.  

```python
CHAT_MODEL: ModelSpec = {
    'name': 'OpenAI',
    'llm': {
        'cls': ChatOpenAI,
        'init_args': {
            'model': "gpt-4o-mini",
        }
    },
}

# Change source_data_location and vector_store_location to match your environment
COLLECTION: CollectionSpec = {
    'name': 'Docs',
    'source_data_location': 's3://blze-ev-ai-rag-app/pdfs',
    'vector_store_location': 's3://blze-ev-ai-rag-app/vectordb/docs',
    'embeddings': {
        'cls': OpenAIEmbeddings,
        'init_args': {
            'model': "text-embedding-3-large",
        },
    },
}
```

You can change the chat model class from `ChatOpenAI` to 
[any subclass of `langchain_core.language_models.chat_models.BaseChatModel`](https://python.langchain.com/docs/integrations/chat/). 
The contents of the `init_args` dict will be passed as arguments to the chat model constructor. You must change the `model` argument to match the implementation you are using, and you may add additional arguments as required.

For example, you could use [Google Gemini 2.0 Flash](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2#2.0-flash) by reconfiguring `CHAT_MODEL` like this:

```python
# At top of file:
from langchain_google_genai import ChatGoogleGenerativeAI

...

CHAT_MODEL: ModelSpec = {
    'name': 'Google Gemini',
    'llm': {
        'cls': ChatGoogleGenerativeAI,
        'init_args': {
            'model': "gemini-2.0-flash-001",
            'temperature': 0,
            'max_tokens': None,
            'timeout': None,
            'max_retries': 2,
        },
    },
}
```

You would also need to define the necessary environment variables with your Google credentials:

```dotenv
GEMINI_API_KEY=<Google Gemini API key>
GOOGLE_APPLICATION_CREDENTIALS=<Location of Google service account key file>
```

You can similarly reconfigure the embedding model class, using [any subclass of `langchain_core.embeddings.embeddings.Embeddings`](https://python.langchain.com/docs/integrations/text_embedding/). Again, using Google as an example:

```python
# At top of file:
from langchain_google_genai import GoogleGenerativeAIEmbeddings

...

COLLECTION: CollectionSpec = {
    'name': 'Docs',
    'source_data_location': 's3://my-bucket/my_data',
    'vector_store_location': 's3://my-bucket/vectordb/docs',
    'embeddings': {
        'cls': GoogleGenerativeAIEmbeddings,
        'init_args': {
            'model': "models/text-embedding-004",
            'task_type': 'semantic_similarity',
        },
    },
}
```

Technically, you can mix and match chat and embedding models, but, if you were to use different providers, you would need an API key for each one.

## Upload Documents to Backblaze B2

If your documents are not already in Backblaze B2, you must upload them. You can use any S3-compatible GUI or CLI tool
to do so. It's helpful to use a prefix such as `docs/` or `pdfs/` to keep them organized and separate from the vector store.

## Load Documents into the Vector Store

Once you have configured your Backblaze B2 and AI API credentials in `.env` or your environment, and your data locations 
in `mysite/settings.py`, you can load a set of documents into the vector store.

Use the custom `loaddata` command:

```console
% python manage.py loaddata
Deleting existing LanceDB vector store at s3://blze-ev-ai-rag-app/vectordb/docs
Creating LanceDB vector store at s3://blze-ev-ai-rag-app/vectordb/docs
Loading data from s3://blze-ev-ai-rag-app/pdfs in pages of 1000 results
Successfully retrieved page 1 containing 618 result(s) from s3://blze-ev-ai-rag-app/pdfs
Skipping pdfs/.bzEmpty
Skipping pdfs/cloud_storage/.bzEmpty
Loading pdfs/cloud_storage/cloud-storage-about-backblaze-b2-cloud-storage.pdf
Loading pdfs/cloud_storage/cloud-storage-add-file-information-with-the-native-api.pdf
Loading pdfs/cloud_storage/cloud-storage-additional-resources.pdf
...
Loading pdfs/v1_api/s3-put-object.pdf
Loading pdfs/v1_api/s3-upload-part-copy.pdf
Loading pdfs/v1_api/s3-upload-part.pdf
Loaded batch of 614 document(s) from page
Split batch into 2758 chunks
[2025-02-28T01:26:11Z WARN  lance_table::io::commit] Using unsafe commit handler. Concurrent writes may result in data loss. Consider providing a commit handler that prevents conflicting writes.
Added chunks to vector store
Added 614 document(s) containing 2758 chunks to vector store; skipped 4 result(s).
Created LanceDB vector store at s3://blze-ev-ai-rag-app/vectordb/docs. "vectorstore" table contains 2758 rows
```

To test the vector database, you can use the custom `search` command:

```console
 % python manage.py search 'Which B2 native APIs would I use to upload large files?' 
2025-03-01 02:38:07,740 ai_rag_app.management.commands.search INFO     Opening vector store at s3://blze-ev-ai-rag-app/vectordb/docs/openai
2025-03-01 02:38:07,740 ai_rag_app.utils.vectorstore DEBUG    Populating AWS environment variables from the b2 profile
Found 4 docs in 2.30 seconds
2025-03-01 02:38:11,074 ai_rag_app.management.commands.search INFO     
page_content='Parts of a large file can be uploaded and copied in parallel, which can significantly reduce the time it takes to upload terabytes of data. Each part can be  anywhere from 5 MB to 5 GB, and you can pick the size that is most convenient for your application. For best upload performance, Backblaze recommends that you use the recommendedPartSize parameter that is returned by the b2_authorize_account operation.  To upload larger files and data sets, you can use the command-line interface (CLI), the Native API, or an integration, such as Cyberduck.  Usage for Large Files  Generally, large files are treated the same as small files. The costs for the API calls are the same.  You are charged for storage for the parts that you uploaded or copied. Usage is counted from the time the part is stored. When you call the b2_finish_large_file' metadata={'source': 's3://blze-ev-ai-rag-app/pdfs/cloud_storage/cloud-storage-large-files.pdf'}
...
```

## Run the Web App

To start the development server on its default port, 8000:

```console
% python manage.py runserver
2025-03-01 02:39:45,605 ai_rag_app.rag INFO     Opening Docs vector store at s3://blze-ev-ai-rag-app/vectordb/docs/openai
2025-03-01 02:39:45,605 ai_rag_app.utils.vectorstore DEBUG    Populating AWS environment variables from the b2 profile
Performing system checks...

System check identified no issues (0 silenced).
March 01, 2025 - 02:39:46
Django version 5.1.6, using settings 'mysite.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

You may provide the runserver command with the interface and port to which the web app should bind. For example, to
listen on the standard HTTP port on all interfaces, you would use:

```console
% python manage.py runserver 0.0.0.0:80
2025-03-01 02:40:18,048 ai_rag_app.rag INFO     Opening Docs vector store at s3://blze-ev-ai-rag-app/vectordb/docs/openai
2025-03-01 02:40:18,048 ai_rag_app.utils.vectorstore DEBUG    Populating AWS environment variables from the b2 profile
Performing system checks...

System check identified no issues (0 silenced).
March 01, 2025 - 02:40:18
Django version 5.1.6, using settings 'mysite.settings'
Starting development server at http://0.0.0.0:80/
Quit the server with CONTROL-C.
```

## Running in Gunicorn

Django's `runserver` command starts a lightweight development server, which is great for experimenting on your own, 
but is not suitable for production. For production deployments, you should use a [WSGI](https://wsgi.readthedocs.io/en/latest/) server such as [Gunicorn](https://gunicorn.org/).
Gunicorn is included as a dependency in `requirements.txt`, so you can easily use it to run the app. The `config/gunicorn.py` file 
specifies the port on which Gunicorn will listen, the number of worker processed and threads that it will start, etc.  

From the project directory:

```shell
gunicorn --config python:config.gunicorn mysite.wsgi
```

## Running Gunicorn as a service with nginx

On its own, Gunicorn is susceptible to denial-of-service attacks from slow clients, so we strongly recommend [deploying 
Gunicorn behind a proxy server](https://docs.gunicorn.org/en/latest/deploy.html) such as [Nginx](https://nginx.org/). The
project includes `gunicorn.service` and `gunicorn.socket` files in the [`systemd`](systemd) directory and an `nginx.conf` 
file in the [nginx](nginx) directory that you can use as a starting point for your deployment. 

## Running in Docker

You can build a Docker image with the command:

```shell
docker build -t ai-rag-app .
```

You must configure the required environment variables before you can run the app in a container. One way to do so is to
use `docker run`'s `--env-file` option.

If you are using Google Gemini you must also provide a bind mount to a host directory containing the GCP service account
key. For example:

```shell
docker run -p 8000:8000 --env-file .env -v ./creds:/app/creds ai-rag-app
```

## Running a local LLM

As an alternative to using an online LLM such as OpenAI or Google Gemini, you can deploy a local model. We'll use [Ollama](https://ollama.com/), a free, open-source tool, to let us run any of a wide variety of LLMs locally. 

[Download](https://ollama.com/download), install and run the Ollama desktop app.

For this tutorial, you'll need a general purpose model like [Llama 3.1](https://ollama.com/library/llama3.1) and a text embedding model such as [`nomic-embed-text`](https://ollama.com/library/nomic-embed-text). There are three variants of Llama 3.1; we successfully used the default 8B parameters version, `llama3.1:8b`, with the RAG app. If you have more capable hardware, you might want to try the 70B or 405B versions. 

Fetch the models from the command line:

```console
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Install the Python package for LangChain Ollama support: 

```console
% pip install langchain_ollama
```

Add the necessary imports at the top of `mysite/settings.py`:

```python
from langchain_ollama import ChatOllama
from lancedb.embeddings import OllamaEmbeddings
```

Edit the `CHAT_MODEL` and `COLLECTION` configurations lower down in the same file:

```python
# At top of file:
from langchain_ollama import ChatOllama, OllamaEmbeddings

...

CHAT_MODEL: ModelSpec = {
    'name': 'Llama',
    'llm': {
        'cls': ChatOllama,
        'init_args': {
            'model': "llama3.1:8b",
        }
    },
}

# Change source_data_location and vector_store_location to match your environment
COLLECTION: CollectionSpec = {
    'name': 'Docs',
    'source_data_location': 's3://blze-ev-ai-rag-app/pdfs',
    'vector_store_location': 's3://blze-ev-ai-rag-app/vectordb/docs/nomic',
    'embeddings': {
        'cls': OllamaEmbeddings,
        'init_args': {
            'model': "nomic-embed-text",
        },
    },
}
```

You will need to [load data into the vector store](#load-documents-into-the-vector-store) and [run the web app](#run-the-web-app) as explained above.

In our experience, Llama 3.1, running on a 2021 MacBook Pro with an Apple M1 Pro chip and 32 GB of memory, took between 10 and 30 seconds to generated an answer using the Backblaze documentation vector store. This is about double the time taken by GPT‑4o mini via the OpenAI API.   
