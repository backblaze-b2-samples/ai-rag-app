import boto3
from django.core.management.base import BaseCommand
from langchain_community.document_loaders import S3FileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai_rag_app.utils.object_store import parse_s3_uri
from ai_rag_app.utils.vectorstore import delete_vectorstore, create_vectorstore

from mysite.settings import COLLECTION, TEXT_SPLITTER_CHUNK_SIZE, TEXT_SPLITTER_CHUNK_OVERLAP


class Command(BaseCommand):
    help = 'Loads data from the configured bucket into the vector database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--page-size',
            default=1000,
            nargs='?',
            type=int,
            help='Page size for retrieving and processing data. Default = Max = 1000',
        )

        parser.add_argument(
            '--max-results',
            default=-1,
            nargs='?',
            type=int,
            help='Maximum number of results to process. Default = process all results',
        )

        parser.add_argument(
            '--mode',
            default='overwrite',
            nargs='?',
            choices=['overwrite', 'append'],
            help='Overwrite existing vector store or append to it. Default = overwrite',
        )

        parser.add_argument(
            '--extensions',
            default='pdf',
            nargs='?',
            help='Comma-separated list of file extensions to load. Default = pdf',
        )

        parser.add_argument(
            '--load-all',
            action='store_true',
            help='Load all documents regardless of file extension.',
        )

        parser.add_argument(
            '--source-data-location',
            default=COLLECTION['source_data_location'],
            nargs='?',
            help=f'Override source data location.',
        )

        parser.add_argument(
            '--vector-store-location',
            default=COLLECTION['vector_store_location'],
            nargs='?',
            help=f'Override vector store location.',
        )


    def handle(self, *args, **options):
        b2_client = boto3.client('s3')

        source_data_location = options['source_data_location']
        vector_store_location = options['vector_store_location']

        if options['mode'] == 'overwrite':
            delete_vectorstore(b2_client, vector_store_location, self.stdout)

        vectorstore = create_vectorstore(COLLECTION['embeddings'], vector_store_location, self.stdout)

        self.stdout.write(f'Loading data data from {source_data_location} in pages of {options["page_size"]} results')

        bucket_name, source_data_path = parse_s3_uri(source_data_location)
        paginator = b2_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=bucket_name,
            Prefix=source_data_path,
            PaginationConfig={'PageSize': options['page_size']}
        )

        extensions = tuple(f'.{ext.strip()}' for ext in options['extensions'].split(','))
        def should_load_file(key: str):
            return options['load_all'] or key.lower().endswith(extensions)

        done = False
        page_count = 0
        doc_count = 0
        skip_count = 0
        split_count = 0
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=TEXT_SPLITTER_CHUNK_SIZE,
            chunk_overlap=TEXT_SPLITTER_CHUNK_OVERLAP
        )
        for page in page_iterator:
            self.stdout.write(f'Successfully retrieved page {page_count + 1} containing {page['KeyCount']} '
                              f'result(s) from {source_data_location}')

            docs = []
            for obj in page['Contents']:
                object_key = obj['Key']
                if should_load_file(object_key):
                    self.stdout.write(f'Loading {object_key}')
                    loader = S3FileLoader(bucket_name, object_key)
                    docs += loader.load()
                    doc_count += 1
                else:
                    self.stdout.write(f'Skipping {object_key}')
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
            self.style.SUCCESS(f'Created LanceDB vector store at {vector_store_location}. "{table.name}" table contains {table.count_rows()} rows')
        )
