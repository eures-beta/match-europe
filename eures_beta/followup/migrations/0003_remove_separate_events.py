"""Follow-up and conclusion histories now live in matching.MatchEvent."""

from importlib import import_module

from django.db import migrations


def copy_followup(apps, schema_editor):
    import_module('eures_beta.matching.migrations.0037_unify_match_events').copy_events(
        apps, schema_editor, kinds={'followup', 'conclusion'}
    )


def restore_followup(apps, schema_editor):
    import_module(
        'eures_beta.matching.migrations.0037_unify_match_events'
    ).restore_events(apps, schema_editor, kinds={'followup', 'conclusion'})


DROP_GUARDS = """
DROP FUNCTION followup_matchfollowupevent_check_adviser();
DROP FUNCTION followup_matchconclusionevent_check_actor();
"""
RESTORE_GUARDS = """
CREATE FUNCTION followup_matchfollowupevent_check_adviser() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.actor_id AND kind='adviser') THEN
  RAISE EXCEPTION 'Follow-up author must be an adviser' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION followup_matchconclusionevent_check_actor() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.actor_id AND kind=CASE WHEN NEW.action='reported' THEN 'employer' ELSE 'adviser' END) THEN
  RAISE EXCEPTION 'Invalid matching outcome author' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ('followup', '0002_domain_table_names'),
        ('matching', '0037_unify_match_events'),
    ]
    operations = [
        migrations.RunPython(copy_followup, restore_followup),
        migrations.DeleteModel(name='MatchFollowupEvent'),
        migrations.DeleteModel(name='MatchConclusionEvent'),
        migrations.RunSQL(DROP_GUARDS, RESTORE_GUARDS),
    ]
