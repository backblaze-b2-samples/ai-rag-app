# Building a Conversational AI Chatbot Website with Backblaze B2 + LangChain 

This app shows you how to implement a simple Conversational AI chatbot website that uses a large language model (LLM) and [retrieval augmented generation](https://python.langchain.com/docs/concepts/rag/) (RAG) to answer questions based on a collection of documents, such as PDFs, stored in a private [Backblaze B2 Cloud Object Storage](https://www.backblaze.com/cloud-storage) Bucket. The app builds on the techniques introduced in the [Retrieval-Augmented Generation with Backblaze B2](https://github.com/backblaze-b2-samples/ai-rag-examples) samples.

You can ingest your own set of documents from Backblaze B2 or use a prebuilt vector store built from the Backblaze documentation. Once you have configured your vector store, you can use the app's web UI to ask questions; the app will use the vector database and LLM to generate answers. The RAG chain implements [chat history](https://python.langchain.com/docs/concepts/chat_history/), so you can refer back to earlier exchanges in a natural way.

The sample code uses [OpenAI GPT‑4o mini](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/), and I'll explain in this document how you can easily configure an alternate model such as [Google Gemini 2.0 Flash](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2#2.0-flash), [DeepSeek V3](https://api-docs.deepseek.com/news/news1226), or run a local LLM using a technology such as [Ollama](https://ollama.com/). The web UI uses [ChatGPT](https://chatgpt.com/) as inspiration, with some additional instrumentation - each answer includes the execution time of the RAG chain.

[![Short video of chatbot in action](TBD)](https://www.youtube.com/watch?v=vBFwUGL_DaQ)

The app is written in Python and leverages the [Django web framework](https://www.djangoproject.com/),  [LangChain AI framework](https://python.langchain.com/docs/introduction/) and [LanceDB vector database](https://lancedb.github.io/lancedb/), all of which are open source. We used the LangChain tutorials [Build a Retrieval Augmented Generation (RAG) App: Part 1](https://python.langchain.com/docs/tutorials/rag/), [Build a Local RAG Application](https://python.langchain.com/v0.2/docs/tutorials/local_rag/), and [Build a Chatbot](https://python.langchain.com/v0.2/docs/tutorials/chatbot/) in creating the app.

## Contents

<!-- TOC -->
* [Contents](#contents)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Configuration](#configuration)
  * [API Credentials](#api-credentials)
  * [Django Configuration](#django-configuration)
  * [Using DeepSeek](#using-deepseek)
  * [Using other LLMs](#using-other-llms)
* [Upload Documents to Backblaze B2](#upload-documents-to-backblaze-b2)
* [Load Documents into the Vector Store](#load-documents-into-the-vector-store)
* [Run the Web App](#run-the-web-app)
* [Running in Gunicorn](#running-in-gunicorn)
* [Running Gunicorn as a service with nginx](#running-gunicorn-as-a-service-with-nginx)
* [Running in Docker](#running-in-docker)
* [Running a local LLM](#running-a-local-llm)
* [Next Steps](#next-steps)
<!-- TOC -->

## Prerequisites

* [Python 3.13.1](https://www.python.org/downloads/release/python-3131/) (other recent Python versions _should_ work) and `pip`.
* A Backblaze account - [sign up here](https://www.backblaze.com/b2/sign-up.html?referrer=nopref).
* An OpenAI account - [sign up here](https://platform.openai.com/signup) - or [configure access to an alternate LLM](#django-configuration).

## Installation

Clone this repository onto your host, then `cd` into the local repository directory.

```shell
git clone git@github.com:backblaze-b2-samples/ai-rag-app
cd ai-rag-app
```

[Python virtual environments](https://docs.python.org/3/library/venv.html) allow you to encapsulate a project's dependencies; we recommend that you create a virtual environment thus:

```shell
python3 -m venv .venv
```

You must then activate the virtual environment before installing dependencies:

```shell
source .venv/bin/activate
```

You will need to reactivate the virtual environment, with the same command, if you close your Terminal window and return to work with the app later.

Now you can use `pip install` to install dependencies:

```shell
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
`COLLECTION` configuration in the sample code point to the Backblaze documentation PDFs and vector store. You can use them with 
the read-only credentials above or change them to match your environment.  

```python
# This is the text that appears in the web UI: "Ask me about {TOPIC}". You can change
# it to match your use case
TOPIC = "Backblaze products"

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
# search_k is the number of results to return when searching the vector store
COLLECTION: CollectionSpec = {
    'name': 'Docs',
    'source_data_location': 's3://blze-ev-ai-rag-app/pdfs',
    'vector_store_location': 's3://blze-ev-ai-rag-app/vectordb/docs',
    'search_k': 4,
    'embeddings': {
        'cls': OpenAIEmbeddings,
        'init_args': {
            'model': "text-embedding-3-large",
        },
    },
}
```

### Using DeepSeek

Unfortunately, [DeepSeek R1 does not play nicely with LangChain](https://www.backblaze.com/blog/experimenting-with-deepseek-backblaze-b2-and-drive-stats/), but [DeepSeek V3](https://api-docs.deepseek.com/news/news1226) is OpenAI-API compatible and works well. You can swap it in with minimal changes:
* In your `.env` file, or however you are setting environment variables, set `OPENAI_API_KEY` to your DeepSeek API key.
* In `mysite/settings.py`, edit the `CHAT_MODEL` configuration:

```python
CHAT_MODEL: ModelSpec = {
    'name': 'DeepSeek',
    'llm': {
        'cls': ChatOpenAI,
        'init_args': {
            'base_url': 'https://api.deepseek.com',
            'model': 'deepseek-chat',
        }
    },
}
```

Note: at present, DeepSeek does not have its own model for creating embeddings. Since document retrieval from the vector 
store is independent of the LLM, you can use OpenAI `text-embedding-3-large` or another embedding model (see below) to
load documents into the vector store.

### Using other LLMs

To use other LLMs, you can change the chat model class from `ChatOpenAI` to 
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
    'search_k': 4,
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

[Click here to learn how to use Ollama to run local models in the app](#running-a-local-llm).

## Upload Documents to Backblaze B2

If your documents are not already in Backblaze B2, you must upload them. You can use any S3-compatible GUI or CLI tool
to do so. It's helpful to use a prefix such as `docs/` or `pdfs/` to keep them organized and separate from the vector store.

## Load Documents into the Vector Store

Once you have configured your Backblaze B2 and AI API credentials in `.env` or your environment, and your data locations 
in `mysite/settings.py`, you can load a set of documents into the vector store.

Use the custom `load_vector_store` command:

```console
% python manage.py load_vector_store
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

You can ignore the warning message - we will not be running more than one LanceDB writer concurrently, so we don't need to prevent conflicting writes.

The `load_vector_store` command includes some useful options for controlling the process, including overriding the source data and vector store locations configured in `mysite/settings.py`:

```console
% python manage.py load_vector_store --help
usage: manage.py load_vector_store [-h] [--page-size [PAGE_SIZE]] [--max-results [MAX_RESULTS]] [--mode [{overwrite,append}]] [--extensions [EXTENSIONS]] [--load-all] [--source-data-location [SOURCE_DATA_LOCATION]] [--vector-store-location [VECTOR_STORE_LOCATION]] [--version]
                                   [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color] [--skip-checks]

Loads data from the configured bucket into the vector database

options:
  -h, --help            show this help message and exit
  --page-size [PAGE_SIZE]
                        Page size for retrieving and processing data. Default = Max = 1000
  --max-results [MAX_RESULTS]
                        Maximum number of results to process. Default = process all results
  --mode [{overwrite,append}]
                        Overwrite existing vector store or append to it. Default = overwrite
  --extensions [EXTENSIONS]
                        Comma-separated list of file extensions to load. Default = pdf
  --load-all            Load all documents regardless of file extension.
  --source-data-location [SOURCE_DATA_LOCATION]
                        Override source data location.
  --vector-store-location [VECTOR_STORE_LOCATION]
                        Override vector store location.
  ...
```

When `--mode` is set to `append`, the `load_vector_store` command adds only those documents that have not already been loaded.

To test the vector database, you can use the custom `search_vector_store` command:

```console
 % python manage.py search_vector_store 'Which B2 native APIs would I use to upload large files?' 
2025-03-01 02:38:07,740 ai_rag_app.management.commands.search INFO     Opening vector store at s3://blze-ev-ai-rag-app/vectordb/docs/openai
2025-03-01 02:38:07,740 ai_rag_app.utils.vectorstore DEBUG    Populating AWS environment variables from the b2 profile
Found 4 docs in 2.30 seconds
2025-03-01 02:38:11,074 ai_rag_app.management.commands.search INFO     
page_content='Parts of a large file can be uploaded and copied in parallel, which can significantly reduce the time it takes to upload terabytes of data. Each part can be  anywhere from 5 MB to 5 GB, and you can pick the size that is most convenient for your application. For best upload performance, Backblaze recommends that you use the recommendedPartSize parameter that is returned by the b2_authorize_account operation.  To upload larger files and data sets, you can use the command-line interface (CLI), the Native API, or an integration, such as Cyberduck.  Usage for Large Files  Generally, large files are treated the same as small files. The costs for the API calls are the same.  You are charged for storage for the parts that you uploaded or copied. Usage is counted from the time the part is stored. When you call the b2_finish_large_file' metadata={'source': 's3://blze-ev-ai-rag-app/pdfs/cloud_storage/cloud-storage-large-files.pdf'}
...
```

The `search_vector_store` command also allows you to override the vector store location configured in `mysite/settings.py`:

```console
% python manage.py search_vector_store --help
usage: manage.py search_vector_store [-h] [--max-results [MAX_RESULTS]] [--vector-store-location [VECTOR_STORE_LOCATION]] [--version] [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color] [--skip-checks] search-string

Searches the vector database for a string

positional arguments:
  search-string         Search the database for this string

options:
  -h, --help            show this help message and exit
  --max-results [MAX_RESULTS]
                        Maximum number of results to process. Default = process all results
  --vector-store-location [VECTOR_STORE_LOCATION]
                        Override vector store location.
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

Once the development server has started, open the URL, for example `http://127.0.0.1:8000/`, in your browser. You should 
see the chatbot web UI:

<img width="1446" alt="Chatbot web UI" src="https://github.com/user-attachments/assets/b6125ed1-ebea-4814-b3e7-d462bec37273" />

Ask a question relating to your document collection:

<img width="1446" alt="Asking a question" src="https://github.com/user-attachments/assets/6d661be9-516c-411f-9995-61c1cf3a6c65" />


<a id="debug-output"></a>
By default, the log level is set to `DEBUG`, and the `RAG` class logs the question, the documents retrieved from the 
vector store, and the answer from the LLM:

```text
2025-03-04 19:03:03,762 ai_rag_app.rag DEBUG    Synchronously invoking the chain with question: Tell me about application keys
2025-03-04 19:03:06,931 ai_rag_app.utils.chain DEBUG    Documents from vector store: [
    {
        "py/object": "langchain_core.documents.base.Document",
        "py/state": {
            "__dict__": {
                "id": null,
                "metadata": {
                    "source": "s3://metadaddy-langchain-demo/pdfs/cloud_storage/cloud-storage-back-up-storage-volumes-from-coreweave-to-backblaze-b2.pdf"
                },
                "page_content": "Application keys control access to your Backblaze B2 Cloud Storage account and the buckets that are contained in your account.\n\n3. Click Add a New Application Key, and enter an app key name.\n\nYou cannot search an app key by this name; therefore, app key names are not required to be globally unique.\n\n4. Select All or a specific bucket in the Allow Access to Bucket(s) dropdown menu.\n\n5. Optionally, select your access type (Read and Write, Read Only, or Write Only).\n\n6. Optionally, select the Allow List All Bucket Names checkbox (required for the B2 Native API b2_list_buckets and the S3-Compatible API S3 List Buckets\n\noperations).\n\n7. Optionally, enter a file name prefix to restrict application key access only to files with that prefix. Depending on what you selected in step #4, this limits\n\napplication key access to files with the specified prefix for all buckets or just the selected bucket.",
                "type": "Document"
            },
            "__pydantic_extra__": null,
            "__pydantic_fields_set__": {
                "py/set": [
                    "metadata",
                    "page_content"
                ]
            },
            "__pydantic_private__": null
        }
    },
    {
        "py/object": "langchain_core.documents.base.Document",
        "py/state": {
            "__dict__": {
                "id": null,
                "metadata": {
                    "source": "s3://metadaddy-langchain-demo/pdfs/cloud_storage/cloud-storage-configure-s3-browser-with-backblaze-b2.pdf"
                },
                "page_content": "Application keys control access to your Backblaze B2 Cloud Storage account and the buckets that are contained in your account.\n\n3. Click Add a New Application Key, and enter an app key name.\n\nYou cannot search an app key by this name; therefore, app key names are not required to be globally unique.\n\n4. Select All or a specific bucket in the Allow Access to Bucket(s) dropdown menu.\n\n5. Optionally, select your access type (Read and Write, Read Only, or Write Only).\n\n6. Optionally, select the Allow List All Bucket Names checkbox (required for the B2 Native API b2_list_buckets and the S3-Compatible API S3 List Buckets\n\noperations).\n\n7. Optionally, enter a file name prefix to restrict application key access only to files with that prefix. Depending on what you selected in step #4, this limits\n\napplication key access to files with the specified prefix for all buckets or just the selected bucket.",
                "type": "Document"
            },
            "__pydantic_extra__": null,
            "__pydantic_fields_set__": {
                "py/set": [
                    "metadata",
                    "page_content"
                ]
            },
            "__pydantic_private__": null
        }
    },
    {
        "py/object": "langchain_core.documents.base.Document",
        "py/state": {
            "__dict__": {
                "id": null,
                "metadata": {
                    "source": "s3://metadaddy-langchain-demo/pdfs/cloud_storage/cloud-storage-integrate-arq-7-immutable-backups-with-backblaze-b2.pdf"
                },
                "page_content": "Application keys control access to your Backblaze B2 Cloud Storage account and the buckets that are contained in your account.\n\n3. Click Add a New Application Key, and enter an app key name.\n\nYou cannot search an app key by this name; therefore, app key names are not required to be globally unique.\n\n4. Select All or a specific bucket in the Allow Access to Bucket(s) dropdown menu.\n\n5. Optionally, select your access type (Read and Write, Read Only, or Write Only).\n\n6. Optionally, select the Allow List All Bucket Names checkbox (required for the B2 Native API b2_list_buckets and the S3-Compatible API S3 List Buckets\n\noperations).\n\n7. Optionally, enter a file name prefix to restrict application key access only to files with that prefix. Depending on what you selected in step #4, this limits\n\napplication key access to files with the specified prefix for all buckets or just the selected bucket.",
                "type": "Document"
            },
            "__pydantic_extra__": null,
            "__pydantic_fields_set__": {
                "py/set": [
                    "metadata",
                    "page_content"
                ]
            },
            "__pydantic_private__": null
        }
    },
    {
        "py/object": "langchain_core.documents.base.Document",
        "py/state": {
            "__dict__": {
                "id": null,
                "metadata": {
                    "source": "s3://metadaddy-langchain-demo/pdfs/cloud_storage/cloud-storage-configure-a-veeam-cloud-repository-recovery-from-backblaze-b2.pdf"
                },
                "page_content": "Application keys control access to your Backblaze B2 Cloud Storage account and the buckets that are contained in your account.\n\n3. Click Add a New Application Key, and enter an app key name.\n\nYou cannot search an app key by this name; therefore, app key names are not required to be globally unique.\n\n4. Select All or a specific bucket in the Allow Access to Bucket(s) dropdown menu.\n\n5. Optionally, select your access type (Read and Write, Read Only, or Write Only).\n\n6. Optionally, select the Allow List All Bucket Names checkbox (required for the B2 Native API b2_list_buckets and the S3-Compatible API S3 List Buckets\n\noperations).\n\n7. Optionally, enter a file name prefix to restrict application key access only to files with that prefix. Depending on what you selected in step #4, this limits\n\napplication key access to files with the specified prefix for all buckets or just the selected bucket.",
                "type": "Document"
            },
            "__pydantic_extra__": null,
            "__pydantic_fields_set__": {
                "py/set": [
                    "metadata",
                    "page_content"
                ]
            },
            "__pydantic_private__": null
        }
    }
], {}
2025-03-04 19:03:11,607 ai_rag_app.rag DEBUG    Received answer: Application keys control access to your Backblaze B2 Cloud Storage account and the buckets contained within that account. Here’s a brief overview of the steps involved in creating and managing application keys:

1. **Creating an Application Key**: You begin by clicking "Add a New Application Key," where you can enter a name for the app key. It is important to note that the name you choose does not need to be globally unique since you cannot search for app keys by name.

2. **Setting Bucket Access**: You can specify access for either all buckets or a specific bucket from the "Allow Access to Bucket(s)" dropdown menu.

3. **Access Types**: You have the option to select the type of access, including Read and Write, Read Only, or Write Only.

4. **List All Bucket Names**: Optionally, you can select the "Allow List All Bucket Names" checkbox. This is required if you plan to use certain API operations.

5. **File Name Prefix**: Additionally, you can enter a file name prefix to restrict application key access to files that match the specified prefix. This applies depending on your selection in the bucket access step.

These features allow you to manage and control how different applications interact with your cloud storage resources.
```

Ask a follow-up question to test conversation history:

<img width="1446" alt="Asking a follow-up question" src="https://github.com/user-attachments/assets/66ab2ede-cc44-49c8-8bee-75450645cdc5" />

Ask it to write some code for you:

<img width="1448" alt="Asking the chatbot to write some code" src="https://github.com/user-attachments/assets/fd73f648-5df6-4ad0-add8-4a9780f294a8" />

If the chatbot seems to go off-topic, you can press the "New Chat" button to clear the history and start a new conversation.

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
# search_k is the number of results to return when searching the vector store  
COLLECTION: CollectionSpec = {
    'name': 'Docs',
    'source_data_location': 's3://blze-ev-ai-rag-app/pdfs',
    'vector_store_location': 's3://blze-ev-ai-rag-app/vectordb/docs/nomic',
    'search_k': 4,
    'embeddings': {
        'cls': OllamaEmbeddings,
        'init_args': {
            'model': "nomic-embed-text",
        },
    },
}
```

You will need to [load data into the vector store](#load-documents-into-the-vector-store) and [run the web app](#run-the-web-app) as explained above.

In our experience, Llama 3.1, running on a 2021 MacBook Pro with an Apple M1 Pro chip and 32 GB of memory, took between 10 and 30 seconds to generate an answer using the Backblaze documentation vector store. This is about double the time taken by GPT‑4o mini via the OpenAI API.   

## Next Steps

This is a sample application, intended to quickly get you started building a conversational AI chatbot with RAG. There 
are many ways you could extend the base application to better meet your needs. Here are a few ideas:

* As you can see in the [debug output](#debug-output), the vector store contains the S3 URL of each document. You could add code to 
generate a clickable `https` URL from the S3 URL and provide links to the documents alongside the LLM's response in the web UI.
* The app uses the default Django support for synchronous I/O and LangChain's synchronous methods, for example, 
[`invoke()`](https://python.langchain.com/api_reference/core/runnables/langchain_core.runnables.base.Runnable.html#langchain_core.runnables.base.Runnable.invoke). 
You could port the app to use [Django's asynchronous support](https://docs.djangoproject.com/en/5.1/topics/async/) and
LangChain's asynchronous methods, such as [`ainvoke`](https://python.langchain.com/api_reference/core/runnables/langchain_core.runnables.base.Runnable.html#langchain_core.runnables.base.Runnable.ainvoke).

Again, in order to get you started quickly, we streamlined the application in several ways. There are a few areas to attend to 
if you wish to run this app in a production setting:  

* The app does not use a database for user accounts, or any other data, so there is no authentication. All access is anonymous.
If you wished to have users log in, you would need to restore Django's
[`AuthenticationMiddleware`](https://docs.djangoproject.com/en/5.1/ref/middleware/#module-django.contrib.auth.middleware) 
class to the `MIDDLEWARE` configuration and [configure a database](https://docs.djangoproject.com/en/5.1/ref/databases/).
* Sessions are stored in memory. As explained above, [you can use Gunicorn to scale the application to multiple threads](#running-in-gunicorn), 
but you would need to [configure a Django session backend](https://docs.djangoproject.com/en/5.1/topics/http/sessions/) to 
run the app in multiple processes or on multiple hosts.
* Similarly, conversation history is stored in memory, so you would need to use a persistent message history implementation,
such as [RedisChatMessageHistory](https://python.langchain.com/api_reference/redis/chat_message_history/langchain_redis.chat_message_history.RedisChatMessageHistory.html) to run the app in multiple processes or on multiple hosts.
