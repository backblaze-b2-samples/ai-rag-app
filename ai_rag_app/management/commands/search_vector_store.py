# MIT License
#
# Copyright (c) 2025 Backblaze, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
from time import perf_counter

from django.core.management import BaseCommand

from ai_rag_app.utils.vectorstore import open_vectorstore
from mysite.settings import DOCUMENT_COLLECTION

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
            "--max-results",
            nargs='?',
            type=int,
            help="Maximum number of results to process. Default = process all results",
        )

        parser.add_argument(
            '--vector-store-location',
            default=DOCUMENT_COLLECTION['vector_store_location'],
            nargs='?',
            help=f'Override vector store location.',
        )

    def handle(self, *args, **options):
        vector_store_location = options['vector_store_location']
        logger.info(f'Opening vector store at {vector_store_location}')
        vectorstore = open_vectorstore(DOCUMENT_COLLECTION['embeddings'], vector_store_location, check_table_exists=True)

        start_time = perf_counter()
        search_results = vectorstore.similarity_search(options['search-string'], k=options['max_results'])
        duration = perf_counter() - start_time
        self.stdout.write(f'Found {len(search_results)} docs in {duration:.2f} seconds')

        for search_result in search_results:
            # Remove newlines so search results are more compact and readable
            search_result.page_content = search_result.page_content.replace('\n', ' ')
            logger.info(f'\n{search_result}')
