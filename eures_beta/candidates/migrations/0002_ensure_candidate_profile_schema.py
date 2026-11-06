"""Reconcile databases whose retired prototype already recorded 0001_initial."""

from django.db import migrations


def ensure_profile_schema(apps, schema_editor):
    Profile = apps.get_model('candidates', 'CandidateProfile')
    if Profile._meta.db_table in schema_editor.connection.introspection.table_names():
        # Fresh installations already ran the current 0001, including its guards.
        return
    schema_editor.create_model(Profile)
    schema_editor.execute("""
        CREATE FUNCTION candidates_require_candidate_account()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM users_user
                WHERE id = NEW.user_id AND kind = 'candidate'
            ) THEN
                RAISE EXCEPTION 'A candidate account is required'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER candidates_profile_account_kind
        BEFORE INSERT OR UPDATE OF user_id ON candidates_candidateprofile
        FOR EACH ROW EXECUTE FUNCTION candidates_require_candidate_account();
        """)


class Migration(migrations.Migration):
    dependencies = [('candidates', '0001_initial')]
    operations = [
        # Reversal leaves the table intact: it belongs to the state of 0001.
        # Reversing 0001 itself remains the explicit table-removal operation.
        migrations.RunPython(ensure_profile_schema, migrations.RunPython.noop),
    ]
