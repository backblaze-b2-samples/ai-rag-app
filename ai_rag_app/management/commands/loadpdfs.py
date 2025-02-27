import os
from fnmatch import fnmatch

import boto3
from django.core.management.base import BaseCommand
from langchain_community.document_loaders import S3FileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai_rag_app.types import EmbeddingsSpec
from ai_rag_app.utils.vectorstore import delete_vectorstore, create_vectorstore
from django.conf import settings


class Command(BaseCommand):
    help = "Loads PDFs from the configured bucket into the vector database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-size",
            default=1000,
            nargs='?',
            type=int,
            help="Page size for retrieving and processing PDFs. Default = Max = 1000",
        )

        parser.add_argument(
            "--max-results",
            default=-1,
            nargs='?',
            type=int,
            help="Maximum number of results to process. Default = process all results",
        )

        parser.add_argument(
            "--mode",
            default='overwrite',
            const='overwrite',
            nargs='?',
            choices=['overwrite', 'append'],
            help="Overwrite existing vector store or append to it. Default = overwrite",
        )

    def handle(self, *args, **options):
        b2_client = boto3.client('s3')

        embeddings: EmbeddingsSpec = settings.COLLECTION['embeddings']

        location = str(os.path.join(
            settings.VECTOR_DB_LOCATION,
            settings.DOCS_COLLECTION_PATH,
        ))

        if options['mode'] == 'overwrite':
            delete_vectorstore(b2_client, settings.BUCKET_NAME, location, self.stdout)

        vectorstore = create_vectorstore(embeddings, settings.BUCKET_NAME, location, self.stdout)

        self.stdout.write(f'Loading PDF data from s3://{settings.BUCKET_NAME}/{settings.PDF_LOCATION} '
                          f'in pages of {options["page_size"]} results')

        paginator = b2_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=settings.BUCKET_NAME,
            Prefix=settings.PDF_LOCATION,
            PaginationConfig={'PageSize': options['page_size']}
        )

        done = False
        page_count = 0
        doc_count = 0
        skip_count = 0
        split_count = 0
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.TEXT_SPLITTER_CHUNK_SIZE,
            chunk_overlap=settings.TEXT_SPLITTER_CHUNK_OVERLAP
        )
        for page in page_iterator:
            self.stdout.write(f'Successfully retrieved page {page_count + 1} containing {page["KeyCount"]} '
                              f'result(s) from {settings.BUCKET_NAME}/{settings.PDF_LOCATION}')

            docs = []
            for obj in page['Contents']:
                # Only process PDF files
                if fnmatch(obj['Key'], '*.pdf'):
                    self.stdout.write(f'Loading {obj["Key"]}')
                    loader = S3FileLoader(settings.BUCKET_NAME, obj['Key'])
                    docs += loader.load()
                    doc_count += 1
                else:
                    self.stdout.write(f'Skipping {obj["Key"]}')
                    skip_count += 1
                if options['max_results'] is not None and doc_count + skip_count == options['max_results']:
                    done = True
                    break

            self.stdout.write(f'Loaded batch of {len(docs)} document(s) from page')

            splits = text_splitter.split_documents(docs)
            split_count += len(splits)
            self.stdout.write(f'Split batch into {len(splits)} chunks')

            vectorstore.add_documents(splits)
            self.stdout.write(f'Added chunks to vector store')

            page_count += 1
            if done:
                break

        self.stdout.write(f'Added {doc_count} document(s) containing {split_count} chunks to vector store; '
                          f'skipped {skip_count} result(s).')
        table = vectorstore._table  # noqa
        self.stdout.write(
            self.style.SUCCESS(f'Created LanceDB vector store for {settings.DOCS_COLLECTION_PATH}. "{table.name}" table contains {table.count_rows()} rows')
        )
