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

import copy

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from ai_rag_app.utils.session import use_session_key
from ai_rag_app.utils.markdown import markdown_to_html
from django.conf import settings


@use_session_key
def index(request: HttpRequest) -> HttpResponse:
    if request.GET.get("newchat", False):
        settings.RAG_INSTANCE.new_chat(request.session.session_key)

    if request.session.session_key in settings.RAG_INSTANCE.store:
        messages = copy.deepcopy(settings.RAG_INSTANCE.store[request.session.session_key].messages)
        for message in messages:
            message.content = markdown_to_html(message.content.strip())
    else:
        messages = []
    context = {
        "rag": settings.RAG_INSTANCE,
        "model_version": settings.CHAT_MODEL['llm']['init_args']['model'],
        "messages": messages,
        "topic": settings.TOPIC,
    }
    return render(request, "ai_rag_app/index.html", context)
