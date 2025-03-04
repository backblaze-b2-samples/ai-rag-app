import logging
import os

import botocore.session
from botocore.client import BaseClient
from django.core.management.base import OutputWrapper
from langchain_community.vectorstores import LanceDB

from ai_rag_app.types import EmbeddingsSpec
from ai_rag_app.utils.object_store import location_has_objects, delete_all

logger = logging.getLogger(__name__)

AWS_ENV_VARS = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION', 'AWS_ENDPOINT_URL']


def check_and_set_lancedb_endpoint_env_vars():
    # LanceDB does not respect AWS_PROFILE, so, if AWS_PROFILE is set and not all of the four individual
    # AWS environment variables are set, set them here.
    if 'AWS_PROFILE' in os.environ and len(list(set(AWS_ENV_VARS) & set(os.environ))) < len(AWS_ENV_VARS):
        logger.debug(f'Populating AWS environment variables from the {os.environ['AWS_PROFILE']} profile')
        session = botocore.session.get_session()
        profile = session.profile
        os.environ['AWS_ACCESS_KEY_ID'] = session.full_config['profiles'][profile]['aws_access_key_id']
        os.environ['AWS_SECRET_ACCESS_KEY'] = session.full_config['profiles'][profile]['aws_secret_access_key']
        os.environ['AWS_DEFAULT_REGION'] = session.full_config['profiles'][profile]['region']
        os.environ['AWS_ENDPOINT_URL'] = session.full_config['profiles'][profile]['endpoint_url']


def open_vectorstore(embeddings: EmbeddingsSpec, uri: str, check_table_exists: bool=False) -> LanceDB:
    # check_and_set_lancedb_endpoint_env_vars()

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


def delete_vectorstore(client: BaseClient, uri: str, out: OutputWrapper | None=None) -> None:
    if location_has_objects(client, uri):
        write_or_log(out, f'Deleting existing LanceDB vector store at {uri}')
        delete_all(client, uri)


def create_vectorstore(embeddings_: EmbeddingsSpec, uri: str, out: OutputWrapper | None=None) -> LanceDB:
    write_or_log(out, f'Creating LanceDB vector store at {uri}')
    return open_vectorstore(embeddings_, uri)
