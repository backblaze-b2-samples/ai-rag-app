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
            message.content = markdown_to_html(message.content)
    else:
        messages = []
    context = {
        "rag": settings.RAG_INSTANCE,
        "model_version": settings.CHAT_MODEL['llm']['init_args']['model'],
        "messages": messages,
        "topic": settings.TOPIC,
    }
    return render(request, "ai_rag_app/index.html", context)
