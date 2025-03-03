from typing import TypedDict, Type, Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel


class EmbeddingsSpec(TypedDict):
    cls: Type[Embeddings]
    init_args: dict[str, Any]

class CollectionSpec(TypedDict):
    name: str
    source_data_location: str
    vector_store_location: str
    embeddings: EmbeddingsSpec

class LLMSpec(TypedDict):
    cls: Type[BaseChatModel]
    init_args: dict[str, Any]

class ModelSpec(TypedDict):
    name: str
    llm: LLMSpec
