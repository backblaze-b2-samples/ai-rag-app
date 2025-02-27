from functools import wraps
from typing import Callable, Any, Optional

from django.http import HttpResponse, HttpRequest
from rest_framework.request import Request
from rest_framework.response import Response


def use_session_key(function: Callable[[Request | HttpRequest, Optional[Any]], Response | HttpResponse]):
    """
    Ensure `session_key` is set before function is called
    """
    @wraps(function)
    def wrap(request: Request | HttpRequest, *args: Any, **kwargs: Any) -> Response | HttpResponse:
        if not request.session.session_key:
            request.session.create()
        return function(request, *args, **kwargs)
    return wrap
