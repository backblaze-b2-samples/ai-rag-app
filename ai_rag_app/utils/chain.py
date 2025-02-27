import logging
import traceback
from time import perf_counter
from typing import Any, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.utils import Input

logger = logging.getLogger(__name__)

class ChainElapsedTime(BaseCallbackHandler):
    """
    Add the time taken to execute a named chain to its output
    """
    def __init__(self, name, *, output_message_key="output", **kwargs):
        super().__init__(**kwargs)
        self.runs = {}
        self.name = name
        self.output_message_key = output_message_key

    def on_chain_start(
            self,
            serialized: dict[str, Any],
            inputs: dict[str, Any],
            run_id: UUID,
            parent_run_id: UUID | None = None,
            tags: list[str] | None = None,
            metadata: dict[str, Any] | None = None,
            **kwargs,
    ) -> None:
        """
        If this is the right chain, save the start time under the run_id
        """
        if kwargs.get("name") == self.name:
            self.runs[run_id] = perf_counter()

    def on_chain_end(
            self,
            outputs: dict[str, Any],
            run_id: UUID,
            parent_run_id: UUID | None = None,
            **kwargs,
    ) -> None:
        """
        If we saved the start time, add the elapsed time to the output message
        """
        run = self.runs.get(run_id)
        if run:
            elapsed = perf_counter() - self.runs.pop(run_id)
            output_val = outputs[self.output_message_key]
            if isinstance(output_val, str):
                outputs[self.output_message_key] = AIMessage(content=output_val, response_metadata={"elapsed": elapsed})
            elif isinstance(output_val, BaseMessage):
                outputs[self.output_message_key].response_metadata["elapsed"] = elapsed

    def on_chain_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            parent_run_id: Optional[UUID] = None,
            **kwargs: Any,
    ) -> None:
        run = self.runs.get(run_id)
        if run:
            stack_trace = traceback.format_exc()
            print(f"Chain error: {error}: {stack_trace}")


def log_input(prefix: str) -> RunnableLambda:
    """
    Log the data flowing through the chain at a given point
    """
    def dumper(data: Input, **kwargs: Any):
        logger.debug(f'{prefix}: {data}, {kwargs}')
        return data
    return RunnableLambda(dumper)
