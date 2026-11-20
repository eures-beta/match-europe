"""A candidate profile belongs to the same candidate account for its lifetime."""

from django.db import migrations

FORWARD = """
LOCK TABLE candidates_candidateprofile IN SHARE ROW EXCLUSIVE MODE;
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM candidates_candidateprofile p
        JOIN users_user u ON u.id = p.user_id WHERE u.kind <> 'candidate'
    ) THEN
        RAISE EXCEPTION 'Candidate profile refers to a non-candidate account';
    END IF;
END $$;
CREATE FUNCTION candidates_candidateprofile_prevent_account_change()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
        RAISE EXCEPTION 'Candidate profile account is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER candidates_candidateprofile_account_immutable
BEFORE UPDATE OF user_id ON candidates_candidateprofile
FOR EACH ROW EXECUTE FUNCTION candidates_candidateprofile_prevent_account_change();
"""

REVERSE = """
DROP TRIGGER candidates_candidateprofile_account_immutable ON candidates_candidateprofile;
DROP FUNCTION candidates_candidateprofile_prevent_account_change();
"""


class Migration(migrations.Migration):
    dependencies = [('candidates', '0010_move_profile_review_suggestion')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
