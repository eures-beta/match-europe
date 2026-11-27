"""English model names for admin only; never mutate shared model metadata."""

from django.utils import translation


class EnglishModelOptions:
    """Delegate native metadata while freezing just the two display names."""

    def __init__(self, options):
        self._options = options
        with translation.override('en'):
            self.verbose_name = str(options.verbose_name)
            self.verbose_name_plural = str(options.verbose_name_plural)

    def __getattr__(self, name):
        return getattr(self._options, name)
