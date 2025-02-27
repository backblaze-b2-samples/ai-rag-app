import logging
import os

from botocore.client import BaseClient
from django.core.management.base import OutputWrapper
from langchain_community.vectorstores import LanceDB

from ai_rag_app.types import EmbeddingsSpec
from ai_rag_app.utils.object_store import prefix_has_objects, delete_all

logger = logging.getLogger(__name__)


def check_and_set_lancedb_endpoint_env_var():
    # Boto3, and by extension S3FS, uses the standard AWS configuration mechanisms. For some reason, LanceDB uses
    # AWS_ENDPOINT, rather than AWS_ENDPOINT_URL, so copy the value if necessary
    if 'AWS_ENDPOINT_URL' in os.environ and not 'AWS_ENDPOINT' in os.environ:
        os.environ['AWS_ENDPOINT'] = os.environ['AWS_ENDPOINT_URL']


def open_vectorstore(embeddings: EmbeddingsSpec, uri: str, check_table_exists: bool=False) -> LanceDB:
    check_and_set_lancedb_endpoint_env_var()

    vectorstore = LanceDB(
        embedding=embeddings['cls'](**embeddings['init_args']),  # noqa - spurious unexpected argument warning
        uri=uri,
        # Need append mode otherwise each call to add_documents
        # overwrites the data written in the previous call!
        # See https://github.com/langchain-ai/langchain/discussions/28295
        mode="append",
    )
    if check_table_exists:
        if vectorstore._table is None:  # noqa
            # Complain loudly now, since it will be easier to diagnose the problem
            raise FileNotFoundError(f'No table found at {uri}')
    return vectorstore


def write_or_log(out: OutputWrapper | None, log_message: str):
    if out:
        out.write(log_message)
    else:
        logger.info(log_message)


def delete_vectorstore(client: BaseClient, bucket: str, location: str, out: OutputWrapper | None=None) -> None:
    if prefix_has_objects(client, bucket, location):
        uri = f's3://{bucket}/{location}'
        write_or_log(out, f'Deleting existing LanceDB vector store at {uri}')
        delete_all(client, bucket, location)


def create_vectorstore(embeddings_: EmbeddingsSpec, bucket: str, location: str, out: OutputWrapper | None=None) -> LanceDB:
    uri = f's3://{bucket}/{location}'
    write_or_log(out, f'Creating LanceDB vector store at {uri}')
    return open_vectorstore(embeddings_, uri)
