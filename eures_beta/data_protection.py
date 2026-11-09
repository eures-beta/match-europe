"""Information inherited from Flask; no automatic deletion or collection enabled."""

from django.utils.translation import gettext_lazy as _, pgettext_lazy

TITLE = _("Data protection and retention")
INTRO = _(
    "This notice carries forward the information and retention periods defined for the Match Europe experiment."
)
SECTIONS = (
    (
        _("Use of your data"),
        _(
            "Your answers help describe your professional project or recruitment needs and organise introductions with human support. Public indicators must be aggregated and anonymised."
        ),
    ),
    (
        _("Access and introductions"),
        _(
            "Access is restricted to authorised teams and technical services needed for the stated purpose. An employer receives only the information needed for a relevant introduction, after the required human validation and agreements. Personal data is not published."
        ),
    ),
)
RETENTION_TITLE = _("Retention periods")
RETENTION_ROWS = (
    (_("Candidate profiles"), _("12 months after the last useful contact.")),
    (
        _("Employer needs"),
        _("12 months after the need is closed or the last useful exchange."),
    ),
    (
        _("Matching records"),
        _("24 months for operational follow-up and decision traceability."),
    ),
    (_("Unanswered invitations"), _("6 months.")),
    (_("Administration and security logs"), _("6 months.")),
    (
        _("Aggregated public statistics"),
        _(
            "Longer retention is possible only for aggregated and anonymised statistics."
        ),
    ),
)
DRAFT_TITLE = _("Temporary questionnaire drafts")
DRAFT_TEXT = _(
    "The candidate draft expires after 2 hours without activity. This temporary draft is separate from a permanently registered profile. Expiry is checked when you return to the questionnaire; it does not guarantee immediate removal from technical storage or backups."
)
SCOPE_TITLE = _("Current scope")
SCOPE_TEXT = _(
    "Your email is verified before the questionnaire. A new account remains inactive until confirmation; answers are saved in your private profile when you submit the questionnaire. Existing profiles are only updated by their signed-in owner. Expired unverified accounts are removed by cleanup, not necessarily at the exact expiry time. Matching and automatic introductions are not activated by this notice."
)
LIMITS = _(
    "These are the retention rules carried forward from the experiment. Automatic deletion according to these periods is not yet implemented in this version. Detailed information about the responsible organisation, the legal basis and deletion arrangements must be completed before collecting real candidate profiles."
)
RIGHTS_TITLE = pgettext_lazy('employer privacy', 'Your rights and contact')

RIGHTS_TEXT = _(
    "You can request access, correction or deletion of your data and ask the project team about its use. Contact the team:"
)
