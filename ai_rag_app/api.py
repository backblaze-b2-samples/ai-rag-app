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

import hashlib
import hmac
import logging

from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import api_view
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from ai_rag_app.utils.session import use_session_key
from ai_rag_app.utils.markdown import markdown_to_html
from django.conf import settings

logger = logging.getLogger(__name__)


@api_view(['POST'])
@use_session_key
def ask_question(request: Request) -> Response:
    response = settings.RAG_INSTANCE.invoke(request.session.session_key, request.data['question'])
    return Response({"answer": markdown_to_html(response.content), "elapsed": response.response_metadata["elapsed"]})


class WebhookAuthentication(BaseAuthentication):
    def authenticate(self, request: Request) -> None:
        """Validate the signature on the event notification message.

        Verify that the x-bz-event-notification-signature header is present,
        well formatted, has the correct version, and matches the HMAC-SHA256
        digest generated from the signing secret and message body.
        """
        if 'x-bz-event-notification-signature' not in request.headers:
            raise NotAuthenticated(detail='Missing signature header')

        signature = request.headers['x-bz-event-notification-signature']
        pair = signature.split('=')
        if len(pair) != 2:
            raise AuthenticationFailed(detail='Invalid signature format')

        version = pair[0]
        if version != 'v1':
            raise AuthenticationFailed(detail='Invalid signature version')

        received_sig = pair[1]
        calculated_sig = hmac.new(
            bytes(settings.EVENT_NOTIFICATIONS_SIGNING_SECRET, 'utf-8'),
            msg=request.body,
            digestmod=hashlib.sha256
        ).hexdigest().lower()

        if received_sig != calculated_sig:
            raise AuthenticationFailed(detail='Invalid signature')

        return None
