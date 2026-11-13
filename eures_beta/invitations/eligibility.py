"""Invitation-specific eligibility, kept outside the authentication model."""


def has_candidate_invitation(user):
    return (
        user.kind == 'candidate'
        and hasattr(user, 'invitation')
        and user.invitation.recipient_kind == 'candidate'
    )
