from django.apps import AppConfig


class MemosConfig(AppConfig):
    name = "apps.memos"
    label = "memos"
    verbose_name = "Memo management and approval"

    def ready(self) -> None:
        from . import access  # noqa: F401  (registers file and export access checks)
