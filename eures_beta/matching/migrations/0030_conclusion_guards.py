"""Full PostgreSQL prefixes and role checks for matching outcomes."""

from django.db import migrations


def normalize(apps, schema_editor):
    quote = schema_editor.quote_name
    for name in ('IntroductionFollowup', 'MatchConclusion', 'MatchConclusionEvent'):
        table = apps.get_model('matching', name)._meta.db_table
        with schema_editor.connection.cursor() as cursor:
            objects = schema_editor.connection.introspection.get_constraints(
                cursor, table
            )
        for old, detail in objects.items():
            if old.startswith(table + '_'):
                continue
            if detail['foreign_key']:
                suffix, kind = 'fk', 'CONSTRAINT'
            elif detail['index']:
                suffix, kind = ('unique_idx' if detail['unique'] else 'idx'), 'INDEX'
            else:
                raise RuntimeError('Unexpected matching outcome schema object')
            new = '_'.join([table, *detail['columns'], suffix])
            if len(new) > 63:
                raise RuntimeError('Matching outcome schema name too long')
            if kind == 'CONSTRAINT':
                schema_editor.execute(
                    f'ALTER TABLE {quote(table)} RENAME CONSTRAINT {quote(old)} TO {quote(new)}'
                )
            else:
                schema_editor.execute(
                    f'ALTER INDEX {quote(old)} RENAME TO {quote(new)}'
                )


GUARDS = """
CREATE FUNCTION matching_matchconclusion_check_roles() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.declared_by_employer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.declared_by_employer_id AND kind='employer') THEN
  RAISE EXCEPTION 'Hiring declarant must be an employer' USING ERRCODE='23514';
 END IF;
 IF NEW.confirmed_by_adviser_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.confirmed_by_adviser_id AND kind='adviser') THEN
  RAISE EXCEPTION 'Matching conclusion requires an adviser' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER matching_matchconclusion_roles_guard BEFORE INSERT OR UPDATE ON matching_matchconclusion
FOR EACH ROW EXECUTE FUNCTION matching_matchconclusion_check_roles();
CREATE FUNCTION matching_matchconclusionevent_check_actor() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM users_user WHERE id=NEW.actor_id AND kind=CASE WHEN NEW.action='reported' THEN 'employer' ELSE 'adviser' END) THEN
  RAISE EXCEPTION 'Invalid matching outcome author' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER matching_matchconclusionevent_actor_guard BEFORE INSERT OR UPDATE ON matching_matchconclusionevent
FOR EACH ROW EXECUTE FUNCTION matching_matchconclusionevent_check_actor();
"""
REVERSE = """
DROP TRIGGER matching_matchconclusionevent_actor_guard ON matching_matchconclusionevent;
DROP FUNCTION matching_matchconclusionevent_check_actor();
DROP TRIGGER matching_matchconclusion_roles_guard ON matching_matchconclusion;
DROP FUNCTION matching_matchconclusion_check_roles();
"""


class Migration(migrations.Migration):
    dependencies = [('matching', '0029_matchconclusion_matchconclusionevent_and_more')]
    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
        migrations.RunSQL(GUARDS, REVERSE),
    ]
