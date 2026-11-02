from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('users', '0001_initial')]
    operations = [
        migrations.RunSQL(
            """
        CREATE FUNCTION users_prevent_kind_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.kind IS DISTINCT FROM OLD.kind THEN
                RAISE EXCEPTION 'User kind is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER users_kind_immutable BEFORE UPDATE OF kind ON users_user
        FOR EACH ROW EXECUTE FUNCTION users_prevent_kind_change();
        """,
            "DROP TRIGGER users_kind_immutable ON users_user; DROP FUNCTION users_prevent_kind_change();",
        )
    ]
