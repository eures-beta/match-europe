"""Conservative local extraction: keep source evidence, never resolve conflicts by guessing."""
import re


def extract_fields(text, data, split_sections=True):
    text = text.replace('ɑ', 'a').replace('\u00a0', ' ')
    lines = []
    for raw in text.splitlines():
        line = re.sub(r'\s+', ' ', raw).strip(' •●▪◦\t')
        if not line or not any(c.isalnum() for c in line):
            continue
        if re.match(r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}', line) or re.match(r'^(?:about:blank|https?://).*\d+/\d+$', line):
            continue
        if re.fullmatch(r'\d+/\d+|Postuler', line, re.I):
            continue
        # These sections belong to the host site, never to the imported job.
        if re.match(r'^(?:POSTULEZ EN LIGNE|Vous pourriez également|Offres similaires|Similar jobs|Ähnliche Stellen|La Newsletter)\b', line, re.I):
            break
        if line not in lines:
            lines.append(line)
    text = '\n'.join(lines)
    data.update(description=text[:16000], extraction='pdf_text', extractionWarnings=[])
    warnings = data['extractionWarnings']

    def warning(field, values):
        warnings.append({'field': field, 'values': list(dict.fromkeys(values))[:8]})

    def unique(values):
        values = list(dict.fromkeys(v.strip() for v in values if v.strip()))
        return values[0] if len(values) == 1 else ''

    # Prefer the explicit job heading after breadcrumbs over navigation or banners.
    start = 0
    for i, line in enumerate(lines[:25]):
        if re.search(r'(?:H/F|M/F|m/f/x|h/f|w/m/d|Product Manager)', line, re.I) and len(line) < 125 and not re.search(r'Accueil|Jobs .*|offres.*emploi|chez .* à ', line, re.I):
            start = i
            break
    head = lines[start:]
    if not head:
        return data
    data['title'] = head[0][:125]
    if len(head) > 2 and re.search(r'télétravail|remote', head[2], re.I):
        data['companyName'] = re.split(r'\s*[·•]|\s+\d[.,]\d|\s*[☆★]', head[1])[0].strip(' -+')[:100]
        data['city'] = head[2][:150]
    if len(head) > 1 and re.match(r'^\d+\s*h(?:eures)?\s*/\s*(?:semaine|week|Woche)', head[1], re.I):
        data['title'] = (head[0] + ' ' + head[1])[:125]
    for i, line in enumerate(head[:8]):
        if re.fullmatch(r"\d{5}\s+[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \-’']+", line) and i == 2:
            data['companyName'], data['city'] = head[i-1][:100], line[:150]
            break

    def labelled(labels):
        found = []
        for i, line in enumerate(lines):
            match = re.fullmatch(labels + r'\s*:\s*(.+)', line, re.I)
            if match:
                found.append(match[1])
            elif re.fullmatch(labels, line, re.I) and i+1 < len(lines):
                found.append(lines[i+1])
        return unique(found)

    data['companyName'] = labelled(r'(?:Nom|Name)') or labelled(r'(?:Entreprise|Company|Unternehmen)') or data['companyName']
    data['city'] = labelled(r'(?:Situation géographique de l’emploi|Situation géographique de l\x27emploi|Job location|Lieu de travail|Arbeitsort)') or data['city']
    # A publication date between title and publisher gives an explicit header boundary.
    for i, line in enumerate(head[:6]):
        if re.match(r'^Publiée le\b', line) and i+2 < len(head):
            data['companyName'], data['city'] = head[i+1][:100], head[i+2][:150]
    # EURES header: title (possibly wrapped), employer, update label.
    for i, line in enumerate(head[:8]):
        if re.match(r'^(?:Mise à jour le|Updated on):?', line, re.I) and i >= 2:
            data['companyName'] = head[i-1][:100]
    for field, label in {'title':r'(?:intitulé du poste|poste|job title|stellenbezeichnung)', 'companyName':r'(?:entreprise|employeur|company|employer|unternehmen|arbeitgeber)', 'city':r'(?:lieu de travail|lieu|workplace|location|arbeitsort)'}.items():
        found = [m[1] for line in lines if (m := re.fullmatch(label+r'\s*:\s*(.+)', line, re.I))]
        if unique(found):
            data[field] = unique(found)[:100 if field == 'companyName' else 125 if field == 'title' else 150]
    # The body can specify a more precise workplace than the country heading.
    place = re.search(r'\bsite de ([A-ZÀ-Ÿ][\wÀ-ÿ-]+) au (Luxembourg)\b', text)
    if place and data['city'] == place[2]:
        data['city'] = ', '.join(place.groups())
    contracts = {'PERMANENT_CONTRACT':r'\bCDI\b', 'FIXED_TERM_CONTRACT':r'\bCDD\b', 'FREELANCE':r'\b(?:indépendant|freelance|independent contractor)\b'}
    found = [kind for kind, pattern in contracts.items() if re.search(pattern, text, re.I)]
    if len(found) == 1:
        data['contractType'] = found[0]
    elif found:
        warning('contractType', found)
    clar = data['clarifications']
    hours = list(dict.fromkeys(re.findall(r'\b\d{1,2}\s*(?:h|heures|hours)\s*/\s*(?:semaine|week|Woche)\b', text, re.I)))
    if len({re.match(r'\d+', h)[0] for h in hours}) > 1:
        warning('hours', hours)
    else:
        schedules = list(dict.fromkeys(re.findall(r'\b(?:temps plein|temps partiel|full-time|part-time|Vollzeit|Teilzeit)\b', text, re.I)))
        clar['hours'] = ' ; '.join(hours + schedules)[:1000]
    salary = re.search(r'\b\d+(?:[.,]\d+)?\s*(?:-|à)\s*\d+(?:[.,]\d+)?\s*(?:EUR|€)\s*(?:par|/|per)\s*(?:heure|hour|Stunde)', text, re.I)
    if salary:
        clar['salary'] = salary[0]
    elif re.search(r"(?:pas de|no) salaire fixe|no fixed salary", text, re.I):
        clar['salary'] = next((l for l in lines if re.search(r"(?:pas de|no) salaire fixe|no fixed salary", l, re.I)), '')[:1000]
        commission = next((l for l in lines if re.search(r'commissions?.*%', l, re.I)), '')
        if commission:
            clar['salary'] = (commission + ' ' + clar['salary'])[:1000]
    experience = re.findall(r'\b\d+\s*\+?\s*(?:ans?|years?|mois|months?)\s+minimum\b|\b\d+\s*\+?\s*years?\s+of\s+[^.\n]{0,80}?experience\b', text, re.I)
    experience += [line for i,line in enumerate(lines) if i and re.fullmatch(r'Experience|Expérience|Berufserfahrung', lines[i-1], re.I)]
    if experience:
        clar['experience'] = ' ; '.join(dict.fromkeys(re.sub(r'\s+', ' ', v).strip() for v in experience))[:1000]
    languages = re.findall(r'\b(French|Français|Französisch|English|Anglais|Englisch|German|Allemand|Deutsch|Luxembourgish|Luxembourgeois|Luxemburgisch)\s*[:–-]?\s*\(?([ABC][12])\b', text, re.I)
    if languages:
        clar['frenchLevel'] = ' ; '.join(dict.fromkeys(f'{language} : {level.upper()}' for language, level in languages))[:1000]
    permits = []
    for line in lines:
        if re.search(r'permis|driving licen[cs]e|Führerschein', line, re.I):
            permits.extend(re.findall(r'\b(?:CE|DE|B|C|D)\b', line))
    if re.search(r'\bCACES\b', text, re.I):
        permits.append('CACES')
    if permits:
        data['requirements'].update(permitRequired='yes', permits=list(dict.fromkeys(permits)))
    profile = [line for line in lines if re.search(r'\bCAP\b|diplômé|experience.*(?:required|essential)', line, re.I)]
    for i, line in enumerate(lines):
        if re.fullmatch(r'Qualifications|Profil recherché|Anforderungen',line,re.I):
            for detail in lines[i+1:]:
                if re.fullmatch(r'Location|Benefits|Lieu|Avantages|Standort',detail,re.I):
                    break
                profile.append(detail)
    data['desiredProfile'] = '\n'.join(profile)[:4000]
    # Remote conditions are source evidence, not a street address for geocoding.
    if re.search(r'\bCET\b', text) and re.search(r'\b(?:remote|télétravail)\b', text, re.I):
        warning('city', [line for line in lines if re.search(r'CET|Grand Est', line)])
    if split_sections:
        missions, profile = document_sections(lines)
        if missions or profile:
            data['description'] = missions[:16000]
            data['desiredProfile'] = profile[:4000]
    return data


def document_sections(lines):
    """Route source sentences without rewriting their requirement strength."""
    headings = {
        'missions': r'(?:description du poste|job description|description|about the role|key responsibilities|votre rôle|vos missions|missions|tâches|aufgaben|ihre aufgaben|tätigkeiten)',
        'profile': r'(?:qualifications|profil recherché|votre profil|profil|compétences(?: et expérience)?|exigences professionnelles|job requirements|qui recherchons-nous\s*\?|requirements|anforderungen|ihr profil|qualifikationen)',
        'conditions': r'(?:benefits|avantages|et mes horaires dans tout ça\s*\?|location|conditions de travail|formation et soutien personnalisés|formation complète|votre réussite financière|arbeitsbedingungen|wir bieten)',
        'skip': r'(?:about us|qui sommes-nous\s*\?|employeur|employer|entreprise|comment postuler|how to apply|étape suivante|interview process|life at .+|job overview|aperçu de l’offre d’emploi|bewerbung|über uns)',
    }
    # Metadata groups can follow the description in the PDF reading order.
    metadata = r'(?:job location|situation géographique de l.emploi|job vacancy|offre d’emploi|détails du poste|temps de travail|type de contrat|langues parlées|expérience professionnelle|niveau d.étude|work schedule|contract type|occupation|number of posts|nombre de postes|date limite de candidature|rémunération|nom|name|legal id|business sector)'
    profile_hint = re.compile(r'\b(?:vous (?:justifiez|possédez|maîtrisez|êtes titulaire)|titulaire|diplômé|CAP\b|CACES|permis|expérience|French|Français|English|Anglais|German|Deutsch|Führerschein|Berufserfahrung|Kenntnisse|Abschluss|Erfahrung|skills?|qualifications?|(?:requires?|proven|direct) experience|ability to|familiarity with|years? of|esprit d’initiative|serviable|dynamique et souriant)\b', re.I)
    mission_hint = re.compile(r'\b(?:mission|responsabilit|vous (?:aurez|serez|réalis|développ|travaill)|livrer|réaliser|utiliser|respecter|vérifier|effectuer|prévenir|contribuer|désossage|découpe|ficelage|emballage|mise en rayon|conseils de cuisine|portefeuille|plans marketing|define and implement|run a robust|lead the|work hand.in.hand)\b', re.I)
    condition_hint = re.compile(r'\b(?:horaires?|planning|travaillez|disponible entre|lundi|dimanche|week.end|temps plein|temps partiel|télétravail|remote|CET|commissions?|salaire fixe|prime|mutuelle|prévoyance|congés|casier judiciaire|casier judicaire|paid|holidays|MacBook|contractor agreement|formations? (?:vous sont|continues)|Arbeitszeit|Homeoffice|Urlaub|Schicht)\b', re.I)
    noise = re.compile(r'(?:https?://|about:blank|postulez|postuler|rejoignez.nous|nous vous avons convaincu|notre grande famille|plein potentiel|opportunité de carrière exceptionnelle|nous vous offrons plus qu.un métier|pourquoi nous rejoindre|est un opérateur global|ses activités se répartissent|partagent une ambition|afin de poursuivre sa croissance|vous rejoignez un groupe|nous croyons en la récompense|nous comprenons que chaque agent|c’est rejoindre une entreprise|c’est intégrer un environnement|boucher chez .*convivialité|une nouvelle recette|allez-y|elle fera peut-être|certains de nos collaborateurs|nous encourageons la diversité|nous garantissons un process|agit pour l’insertion|parlez-nous en|nous vous proposons d’exercer|véritable artisan|découvrez|discover the perks)', re.I)
    buckets = {'missions': [], 'conditions': [], 'profile': []}
    state, buffer = 'unknown', []

    def flush():
        paragraph = ' '.join(buffer)
        buffer.clear()
        # Rejoin printed line wraps, then split sentences and run-together task bullets.
        sentences = re.split(r'(?<=[.!?])\s*(?=[A-ZÀ-Ÿ])|\s*[-–]\s*(?=(?:Livrer|Réaliser|Utiliser|Respecter|Vérifier|Effectuer|Prévenir|Contribuer)\b)|\s+[•●*]\s+', paragraph)
        for sentence in sentences:
            sentence = sentence.strip(' -')
            if not sentence or noise.search(sentence):
                continue
            # Explicit profile evidence wins over a generic description heading.
            target = 'profile' if profile_hint.search(sentence) and not mission_hint.search(sentence) else None
            if target is None and condition_hint.search(sentence):
                target = 'conditions'
            if target is None and state in ('missions', 'profile', 'conditions'):
                target = state
            if target is None and mission_hint.search(sentence):
                target = 'missions'
            if target and state != 'skip' and sentence not in buckets[target]:
                buckets[target].append(sentence)

    for line in lines:
        normalized = line.strip(' :')
        if re.match(r'^(?:Aucun salaire indiqué|Trouvé sur|Continuer pour postuler)', normalized, re.I):
            flush()
            continue
        heading = next((kind for kind, pattern in headings.items() if re.fullmatch(pattern, normalized, re.I)), None)
        if heading:
            flush()
            state = heading
        elif re.fullmatch(metadata, normalized, re.I):
            flush()
            state = 'metadata'
        elif re.fullmatch(r'Languages|Langues|Experience|Expérience|Permis de conduire|Sprachen', normalized, re.I):
            flush()
            state = 'profile'
        else:
            if state == 'metadata' and re.match(r'^(?:Utiliser|Respecter|Vérifier|Effectuer|Prévenir|Contribuer|Vous justifiez)\b', line, re.I):
                flush()
                state = 'unknown'
            buffer.append(line)
    flush()
    # Labels are not translated here: source text keeps its original language.
    missions = '\n\n'.join('\n'.join('- ' + value for value in buckets[kind]) for kind in ('missions', 'conditions') if buckets[kind])
    profile = '\n'.join('- ' + value for value in buckets['profile'])
    return missions, profile
