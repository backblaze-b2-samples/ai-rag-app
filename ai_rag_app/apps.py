import types

from django.apps import AppConfig


class AiRagAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_rag_app'

    def __init__(self, app_name: str, app_module: types.ModuleType | None):
        super().__init__(app_name, app_module)
