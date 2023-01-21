from django.apps import AppConfig


class FindBananasConfig(AppConfig):
    name = 'find_bananas'

    def ready(self):
        from bananas_updater import updater
        updater.start()
