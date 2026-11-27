"""Definition checks: a rename must not leave the old database contract active."""

import hashlib

from django.apps import apps
from django.core.checks import Error, Tags, register

OLD_RELATIONS = {
    'matching.EmployerCandidateReview': {'adviser'},
    'employers.JobOffer': {'created_by'},
    'invitations.Invitation': {'sender'},
    'matching.JobOfferSupport': {'updated_by'},
    'matching.CandidateSupport': {'updated_by'},
    'matching.MatchEvaluation': {'pair'},
    'matching.MatchDecision': {'pair'},
    'matching.CandidateOfferReview': {'pair', 'assigned_to'},
    'matching.CandidateOfferReviewAnswer': {'request'},
    'matching.CandidateProfileSharing': {'request'},
    'matching.CandidateOfferConversation': {'confirmation', 'review'},
}
OLD_REVERSE_RELATIONS = {
    'imports',
    'created_imports',
    'advised_imports',
    'agreements',
    'created_job_offers',
}


def schema_prefix(table, limit=63):
    """Keep room for a useful suffix within Django's shorter index-name limit."""
    if len(table) + 9 <= limit:
        return table + '_'
    digest = hashlib.sha256(table.encode()).hexdigest()[:8]
    return table[: limit - 18] + '_' + digest + '_'


@register(Tags.models)
def check_model_names(app_configs=None, **kwargs):
    errors = []
    configs = app_configs if app_configs is not None else apps.get_app_configs()
    for config in configs:
        if not config.name.startswith('eures_beta.'):
            continue
        for model in config.get_models():
            meta = model._meta
            if meta.proxy or not meta.managed:
                continue
            table = f'{meta.app_label}_{meta.model_name}'
            if meta.db_table != table:
                errors.append(
                    Error(
                        f'{meta.label}: table must be {table}, not {meta.db_table}.',
                        obj=model,
                        id='model_names.E001',
                    )
                )
            for item, limit in [(c, 63) for c in meta.constraints] + [
                (i, i.max_name_length) for i in meta.indexes
            ]:
                prefix = schema_prefix(table, limit)
                if not item.name.startswith(prefix) or len(item.name) > limit:
                    errors.append(
                        Error(
                            f'{meta.label}: schema name {item.name} must start with {prefix} and fit in {limit} characters.',
                            obj=model,
                            id='model_names.E002',
                        )
                    )
            for field in meta.local_fields:
                if field.column != field.attname:
                    errors.append(
                        Error(
                            f'{meta.label}.{field.name}: column must follow its field name ({field.attname}).',
                            obj=field,
                            id='model_names.E005',
                        )
                    )
                if field.name in OLD_RELATIONS.get(meta.label, set()):
                    errors.append(
                        Error(
                            f'{meta.label}.{field.name}: obsolete model relationship.',
                            obj=field,
                            id='model_names.E003',
                        )
                    )
                if (
                    field.is_relation
                    and field.remote_field.related_name in OLD_REVERSE_RELATIONS
                ):
                    errors.append(
                        Error(
                            f'{meta.label}.{field.name}: obsolete reverse relationship {field.remote_field.related_name}.',
                            obj=field,
                            id='model_names.E004',
                        )
                    )
    return errors
