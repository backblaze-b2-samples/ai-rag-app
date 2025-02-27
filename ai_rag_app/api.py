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
    output = settings.RAG_INSTANCE.invoke(request.session.session_key, request.data['question'])
    return Response({"answer": markdown_to_html(output.content), "elapsed": output.response_metadata["elapsed"]})


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
