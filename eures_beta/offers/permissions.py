def allowed_offer(user, offer):
    return user.pk == offer.employer_id or (
        user.profile.verified
        and (user.pk == offer.adviser_id or user.profile.role == 'admin')
    )
