import logging
import os
from typing import Tuple

import botocore.session
import lancedb
from botocore.client import BaseClient
# WORKAROUND
# langchain_community.vectorstores.LanceDB references lancedb.remote.table.RemoteTable without importing it,
# so we have to import it here!
# See https://github.com/langchain-ai/langchain/issues/30124
import lancedb.remote.table
from langchain_community.vectorstores import LanceDB

from ai_rag_app.types import EmbeddingsSpec
from ai_rag_app.utils.object_store import location_has_objects, delete_all

logger = logging.getLogger(__name__)

# Same as default table name in langchain_community.vectorstores.LanceDB
LANCEDB_TABLE_NAME = 'vectorstore'

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


def open_vectorstore_and_table(
    embeddings: EmbeddingsSpec,
    uri: str,
    check_table_exists: bool=False,
) -> Tuple[LanceDB, lancedb.table.Table]:
    """
    Explicitly create the LanceDB connection and table, then use them to create the vectorstore so we can return
    both the vectorstore and the underlying table.
    """
    check_and_set_lancedb_endpoint_env_vars()

    connection = lancedb.connect(uri)
    try:
        lance_table = connection.open_table(LANCEDB_TABLE_NAME)
    except Exception:  # noqa - this is what langchain_community.vectorstores.LanceDB does!
        # Table doesn't exist, but this isn't a problem if we're about to populate it
        if check_table_exists:
            raise FileNotFoundError(f'No table found at {uri}')
        lance_table = None

    vectorstore = LanceDB(
        embedding=embeddings['cls'](**embeddings['init_args']),  # noqa - spurious unexpected argument warning
        # Need append mode otherwise each call to add_documents
        # overwrites the data written in the previous call!
        # See https://github.com/langchain-ai/langchain/discussions/28295
        mode="append",
        connection=connection,
        table=lance_table,
    )
    return vectorstore, lance_table


def open_vectorstore(
        embeddings: EmbeddingsSpec,
        uri: str,
        check_table_exists: bool=False,
) -> LanceDB:
    vectorstore, _ = open_vectorstore_and_table(embeddings, uri, check_table_exists=check_table_exists)
    return vectorstore


def delete_vectorstore(client: BaseClient, uri: str) -> None:
    if location_has_objects(client, uri):
        delete_all(client, uri)
