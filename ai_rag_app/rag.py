import logging
from abc import ABC, abstractmethod
from operator import itemgetter

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableLambda, Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables.utils import Output, Input

from ai_rag_app.types import CollectionSpec, ModelSpec
from ai_rag_app.utils.chain import ChainElapsedTime, log_input
from ai_rag_app.utils.vectorstore import open_vectorstore

logger = logging.getLogger(__name__)


# Based on https://python.langchain.com/docs/tutorials/rag/
# and https://python.langchain.com/v0.2/docs/tutorials/chatbot/
class RAG:
    def __init__(self, collection_spec: CollectionSpec, model_spec: ModelSpec):
        self._store: dict[str, BaseChatMessageHistory] = {}
        self._chain: Runnable = self._create_chain(
            self._create_model(model_spec),
            self._create_retriever(collection_spec),
            self._store
        )
        self._collection_name = collection_spec['name']
        self._model_name = model_spec['name']

    @staticmethod
    def _create_model(model_spec: ModelSpec) -> BaseChatModel:
        # Instantiate a model instance based on the spec
        return model_spec['llm']['cls'](**model_spec['llm']['init_args'])

    @staticmethod
    def _create_retriever(collection_spec: CollectionSpec) -> BaseRetriever:
        # Open the vector store at the configured location and return its retriever
        vector_db_uri = collection_spec['vector_store_location']
        logger.info(f'Opening {collection_spec["name"]} vector store at {vector_db_uri}')
        vectorstore = open_vectorstore(collection_spec['embeddings'], vector_db_uri, check_table_exists=True)
        return vectorstore.as_retriever()

    @staticmethod
    def _get_session_history(store: dict[str, BaseChatMessageHistory], session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

    @staticmethod
    def _create_chain(model: BaseChatModel, retriever: BaseRetriever, store: dict[str, BaseChatMessageHistory]) -> Runnable:
        system_prompt = (
            "Use the following pieces of context and the message history to "
            "answer the question at the end. If you don't know the answer, "
            "just say that you don't know, don't try to make up an answer. "
            "\n\n"
            "Context: {context}")

        prompt = ChatPromptTemplate(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history", optional=True, n_messages=10),
                ("human", "{question}"),
            ]
        )

        # Create the basic chain
        # When loglevel is set to DEBUG, log_input will log the results from the vector store
        chain = (
            {
                "context": (
                    itemgetter("question")
                    | retriever
                    | log_input('Documents from vector store', pretty=True)
                ),
                "question": itemgetter("question"),
                "history": itemgetter("history"),
            }
            | prompt
            | model
            | StrOutputParser()
            | RunnableLambda(lambda x: {"output": x})
        )

        # Give the chain a name so the handler can see it
        named_chain: Runnable[Input, Output] = chain.with_config(run_name="my_chain")

        # Add message history
        return RunnableWithMessageHistory(
            named_chain,
            lambda session_id: RAG._get_session_history(store, session_id),
            input_messages_key="question",
            history_messages_key="history",
        )

    def invoke(self, session_key: str, question: str) -> BaseMessage:
        logger.debug(f'Synchronously invoking the chain with question: {question}')
        response = self._chain.invoke(
            {"question": question},
            config={
                "configurable": {
                    "session_id": session_key
                },
                "callbacks": [
                    ChainElapsedTime("my_chain")
                ]
            },
        )
        logger.debug(f'Received answer: {response["output"].content}')

        return response["output"]

    def new_chat(self, session_id: str) -> None:
        self._store[session_id] = InMemoryChatMessageHistory()

    @property
    def store(self) -> dict[str, BaseChatMessageHistory]:
        return self._store

    @property
    def collection_name(self) -> str:
        return self._collection_name

    @property
    def model_name(self) -> str:
        return self._model_name
