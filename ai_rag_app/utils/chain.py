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
import traceback
import jsonpickle
import json
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
    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.runs = {}
        self.name = name

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
            outputs: BaseMessage,
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
            outputs.response_metadata["elapsed"] = elapsed

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


def log_data(prefix: str, pretty=False) -> RunnableLambda:
    """
    Log the data flowing through the chain at a given point
    """
    def dumper(data: Input, **kwargs: Any):
        data_out = json.dumps(json.loads(jsonpickle.encode(data)), indent=4) if pretty else data
        logger.debug(f'{prefix}: {data_out}, {kwargs}')
        return data
    return RunnableLambda(dumper)


def log_chain(chain, level, config):
    """
    Log an ASCII representation of the chain
    """
    if logger.isEnabledFor(level):
        graph_ascii = chain.get_graph(config=config).draw_ascii()
        logger.log(level, f'Created chain: \n{graph_ascii}')
