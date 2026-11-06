"""Session-private skills selection; never writes profiles or offers."""

from time import time

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from .skills_pilot import SelectionForm, catalogue, choices

SESSION_KEY = 'skills_pilot_v1'
TTL = 30 * 60


def guard(request):
    if not settings.SKILLS_PILOT_ENABLED:
        raise Http404


def language(request):
    value = request.GET.get('lang', 'fr')
    return value if value in ('fr', 'en', 'de') else 'fr'


def destination(role, lang, step='occupation'):
    return f"{reverse('skills_pilot_journey', args=[role])}?lang={lang}&step={step}"


@never_cache
@require_safe
def start(request):
    guard(request)
    with translation.override(language(request)):
        return render(request, 'occupations/pilot.html', {'pilot_start': True})


@never_cache
@require_http_methods(['GET', 'POST'])
def journey(request, role):
    guard(request)
    if role not in ('employer', 'candidate'):
        raise Http404
    lang = language(request)
    with translation.override(lang):
        return _journey(request, role, lang)


def _journey(request, role, lang):
    cards, _skills = catalogue()
    all_states = request.session.get(SESSION_KEY, {})
    state = all_states.get(role, {})
    expired = bool(state and time() - state.get('updated', 0) > TTL)
    if expired:
        all_states.pop(role, None)
        request.session[SESSION_KEY] = all_states
        state = {}
    card = cards.get(state.get('occupation'))
    step = request.GET.get('step', 'occupation')
    if step not in ('occupation', 'skills', 'review'):
        raise Http404
    error = (
        _('This temporary draft expired. Choose the occupation again.')
        if expired
        else ''
    )
    form = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if expired or (action == 'selection' and not card):
            error = _('This temporary draft expired. Choose the occupation again.')
            return render(
                request,
                'occupations/pilot.html',
                _context(role, cards, lang, 'occupation', None, None, error),
                status=409,
            )
        if action == 'restart':
            all_states.pop(role, None)
            request.session[SESSION_KEY] = all_states
            return redirect(destination(role, lang))
        if action == 'occupation':
            selected = request.POST.get('occupation')
            if selected not in cards:
                error = _('Choose one of the pilot occupations.')
                step = 'occupation'
            else:
                if selected != state.get('occupation'):
                    state = {
                        'occupation': selected,
                        'skills': [],
                        'behaviours': [],
                        'other': '',
                        'revision': state.get('revision', 0) + 1,
                        'completed': False,
                    }
                state['updated'] = time()
                all_states[role] = state
                request.session[SESSION_KEY] = all_states
                return redirect(destination(role, lang, 'skills'))
        elif action == 'selection' and card:
            form = SelectionForm(card, lang, request.POST)
            if form.is_valid():
                if form.cleaned_data['occupation'] != state[
                    'occupation'
                ] or form.cleaned_data['revision'] != state.get('revision', 0):
                    error = _(
                        'This draft changed in another tab. Reload before continuing.'
                    )
                else:
                    target_language = request.POST.get('target_language')
                    switching_language = target_language in ('fr', 'en', 'de')
                    state.update(
                        {
                            k: form.cleaned_data[k]
                            for k in ('skills', 'behaviours', 'other')
                        }
                    )
                    state.update(
                        updated=time(),
                        revision=state.get('revision', 0) + 1,
                        completed=(
                            state.get('completed', False)
                            if switching_language
                            else True
                        ),
                    )
                    all_states[role] = state
                    request.session[SESSION_KEY] = all_states
                    return redirect(
                        destination(
                            role,
                            target_language if switching_language else lang,
                            'skills' if switching_language else 'review',
                        )
                    )
            step = 'skills'
        elif action not in ('occupation',):
            raise Http404
    if not card and step != 'occupation':
        return redirect(destination(role, lang))
    if step == 'review' and not state.get('completed'):
        return redirect(destination(role, lang, 'skills'))
    if card and form is None:
        form = SelectionForm(
            card, lang, initial={**state, 'revision': state.get('revision', 0)}
        )
    context = _context(role, cards, lang, step, card, form, error)
    if card:
        context['selected_skills'] = [
            label
            for uri, label in choices(card, 'keySkills', lang)
            if uri in state.get('skills', [])
        ]
        context['selected_behaviours'] = [
            label
            for uri, label in choices(card, 'behaviours', lang)
            if uri in state.get('behaviours', [])
        ]
        context['other'] = state.get('other', '')
        context['current_occupation'] = state.get('occupation')
    return render(
        request,
        'occupations/pilot.html',
        context,
        status=400 if request.method == 'POST' else 200,
    )


def _context(role, cards, lang, step, card, form, error):
    titles = {
        'nettoyage': _('Cleaning — private homes'),
        'nettoyage-locaux': _('Cleaning — offices and buildings'),
        'espaces-verts': _('Green space maintenance'),
        'restauration': _('Restaurant service'),
        'securite': _('Security guard'),
        'agroalimentaire': _('Food production worker'),
        'pret-a-porter': _('Clothing sales assistant'),
    }
    return {
        'role': role,
        'step': step,
        'pilot_cards': [
            (key, titles.get(key, item['occupation']['labels'][lang]))
            for key, item in cards.items()
        ],
        'occupation_label': (
            titles.get(card['id'], card['occupation']['labels'][lang]) if card else ''
        ),
        'occupation_uri': card['occupation']['uri'] if card else '',
        'official_occupation_label': card['occupation']['labels'][lang] if card else '',
        'form': form,
        'pilot_error': error,
    }
