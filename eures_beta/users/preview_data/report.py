"""Read-only counts for active concrete models, without exporting row contents."""

from django.apps import apps


def model_counts():
    return {
        model._meta.label: model.objects.count()
        for model in sorted(apps.get_models(), key=lambda model: model._meta.label)
        if model._meta.managed and not model._meta.proxy
    }


def report(output):
    for label, count in model_counts().items():
        output.write(f'{label}: {count}')
