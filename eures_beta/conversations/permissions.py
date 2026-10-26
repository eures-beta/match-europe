def conversation_allowed(user, conv):
    # Operators do not receive blanket access to private conversations.
    return user.profile.verified and user.pk in [
        conv.match.candidate.user_id,
        conv.match.offer.employer_id,
        conv.match.offer.adviser_id,
    ]
