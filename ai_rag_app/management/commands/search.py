import logging
import os
from time import perf_counter

from django.core.management import BaseCommand

from ai_rag_app.utils.vectorstore import open_vectorstore
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Searches the vector database for a string"

    def add_arguments(self, parser):
        parser.add_argument(
            "search-string",
            type=str,
            help="Search the database for this string",
        )

        parser.add_argument(
            "collection",
            type=str,
            choices=list(set([c['path'] for c in settings.COLLECTIONS])),
            help="Collection to search",
        )

        parser.add_argument(
            "--max-results",
            nargs='?',
            type=int,
            help="Maximum number of results to process. Default = process all results",
        )

    def handle(self, *args, **options):
        path = os.path.join(
            os.environ["BUCKET_NAME"],
            os.environ["VECTOR_DB_LOCATION"],
            options['collection'],
        )
        vector_db_uri = f's3://{path}'
        logger.info(f'Opening {options['collection']} vector store at {vector_db_uri}')
        # TODO - add support for $combined collection
        collection_spec = next(collection for collection in settings.COLLECTIONS if collection['path'] == options['collection'])
        vectorstore = open_vectorstore(collection_spec['embeddings'], vector_db_uri, check_table_exists=True)

        start_time = perf_counter()
        search_results = vectorstore.similarity_search(options['search-string'], k=options['max_results'])
        duration = perf_counter() - start_time
        self.stdout.write(f'Found {len(search_results)} docs in {duration:.2f} seconds')

        for search_result in search_results:
            # Remove newlines so search results are more compact and readable
            search_result.page_content = search_result.page_content.replace('\n', ' ')
            logger.info(f'\n{search_result}')
