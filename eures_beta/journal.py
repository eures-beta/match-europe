"""Public project milestones translated with Django gettext."""

from django.utils.translation import pgettext_lazy

ENTRIES = [
    {
        "id": 'entry-2026-10-01',
        "datetime": '2026-10-01',
        'date': pgettext_lazy("project journal", 'Early October 2026'),
        'title': pgettext_lazy(
            "project journal", 'Welcoming advisers and preparing our work together'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'Colleagues from ADEM, FOREM and France Travail Grand Est joined the work in early October. Their arrival puts the project’s focus on trust and support from field professionals into practice.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Dedicate this phase to welcoming advisers and helping them get to grips with the project. No acquisition campaign was carried out during this period: priority was deliberately given to preparing the work with colleagues from the three organisations.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'Work focuses on helping advisers understand the project and preparing their contribution to the experiment.',
            ),
            pgettext_lazy(
                "project journal",
                'Advisers have started approaching businesses to collect their recruitment needs.',
            ),
            pgettext_lazy(
                "project journal",
                'This phase prepares the continuation of the experiment with identified professionals in direct contact with employers.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Share the first needs collected and advisers’ feedback to adjust the collective work.',
        ),
    },
    {
        "id": 'entry-2026-09-04',
        "datetime": '2026-09-04',
        'date': pgettext_lazy("project journal", 'Since 4 September 2026'),
        'title': pgettext_lazy(
            "project journal", 'Three public employment services commit to the project'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'The first stages of the experiment highlighted the importance of trust in introductions. To collect business needs and start a conversation, the project relies on identified professionals rooted in their local areas.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'From 4 September 2026, ADEM, FOREM and France Travail Grand Est committed to the project. Each of the three organisations allocates one third of a field adviser’s working time to contribute to the experiment.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'The project benefits from the commitment of the three organisations to anchor the experiment in their local areas.',
            ),
            pgettext_lazy(
                "project journal",
                'The contribution of field advisers puts the focus on trust and human support into practice.',
            ),
            pgettext_lazy(
                "project journal",
                'Colleagues joined the work in early October, opening a phase of welcome and familiarisation with the project.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Prepare the arrival of advisers and help them get to grips with the project.',
        ),
    },
    {
        "id": 'entry-2026-08-17',
        "datetime": '2026-08-17',
        'date': pgettext_lazy("project journal", '17 August 2026'),
        'title': pgettext_lazy(
            "project journal",
            'Clarifying Match Europe’s role in a recruitment market saturated by automation',
        ),
        'observed': pgettext_lazy(
            "project journal",
            'An article published in Le Point on 17 August 2026 describes a recruitment market increasingly saturated by the use of artificial intelligence on both sides: candidates optimise CVs and applications to pass filters, while recruiters use automated tools to handle volumes that have become difficult to manage. This dynamic increases noise, favours standardised profiles, weakens the CV as a signal and reinforces the importance of networks, internal mobility and trust in introductions.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Use this reading as a product hypothesis, without treating it as official statistical evidence: Match Europe should organise qualified, explainable, restrained and human introductions rather than add another flow of applications. The service should help explain why a profile is proposed, secure the first contact and track what happens after transmission.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'The CV remains useful, but must not become the sole decision signal.',
            ),
            pgettext_lazy(
                "project journal",
                'Structured answers from candidates and employers should be given greater prominence: availability, mobility, languages, working conditions, documents, salary, contact channel and consent.',
            ),
            pgettext_lazy(
                "project journal",
                'Matching must remain explainable and supervised, with a human decision before transmission.',
            ),
            pgettext_lazy(
                "project journal",
                'Tracking outcomes becomes a central product indicator: actual contact, discussion, interview, refusal, withdrawal, recruitment and reasons for no further action.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Strengthen administration around three objectives: reading profiles more effectively, explaining matching proposals more clearly and measuring introduction outcomes, especially to compare contact channels.',
        ),
    },
    {
        "id": 'entry-2026-08-13',
        "datetime": '2026-08-13',
        'date': pgettext_lazy("project journal", 'August 13, 2026'),
        'title': pgettext_lazy(
            "project journal",
            'Strengthen the public identity and test a more reassuring invitation channel',
        ),
        'observed': pgettext_lazy(
            "project journal",
            'The first email tests show that trust does not depend only on the wording of the message. Even when the target URL is the Match Europe domain, some sending tools rewrite links through a technical tracking domain. For a candidate or an employer, this can immediately look suspicious.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Use matcheurope.beta.francetravail.fr as the public reference address, strengthen the visible identity of the service on public pages, and test invitations sent directly from the France Travail professional mailbox with readable and reassuring URLs.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'Public pages now display Match Europe as the main service name.',
            ),
            pgettext_lazy(
                "project journal",
                'The Match Europe logo is integrated into the public header.',
            ),
            pgettext_lazy(
                "project journal",
                'Test links and admin access links use the France Travail public URL.',
            ),
            pgettext_lazy(
                "project journal",
                'A candidate invitation template is prepared for testing through professional Outlook.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Compare responses from Brevo invitations and from invitations sent through the professional mailbox, then decide which channel should be used for the next wave.',
        ),
    },
    {
        "id": 'entry-2026-08-10',
        "datetime": '2026-08-10',
        'date': pgettext_lazy("project journal", 'August 10, 2026'),
        'title': pgettext_lazy(
            "project journal", 'Test unsolicited applications with a new employer'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'A candidate profile may be relevant to a company that does not yet use Match Europe and has therefore not described a vacancy in the service. Requiring the employer questionnaire before presenting the profile would create unnecessary friction and make it harder to measure simple interest.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Create a separate unsolicited-application flow. The CV is sent to the employer, who can answer ‘Interested’ or ‘Not interested’ without immediately completing a questionnaire. The candidate is informed separately and every send is recorded for follow-up.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'Match Europe can now open a relationship with a new employer through a concrete profile.',
            ),
            pgettext_lazy(
                "project journal",
                'The employer questionnaire is only proposed if the company wants to continue.',
            ),
            pgettext_lazy(
                "project journal",
                'Sends and employer responses can be tracked in the administration area.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Measure responses, delays, exchanges, interviews and hires to assess the usefulness of this new channel.',
        ),
    },
    {
        "id": 'entry-2026-07-20',
        "datetime": '2026-07-20',
        'date': pgettext_lazy("project journal", 'July 2026'),
        'title': pgettext_lazy(
            "project journal", 'Open up the project and document its decisions'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'The project is entering a phase in which several categories of actors need to be able to quickly understand its purpose, results, lessons learned, key choices, method and next steps. A sign-up page alone is not enough for a decision-maker, a partner or a media outlet to present the project properly.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Create a public institutional space built around two complementary pages: The project, presenting the problem, the solution, the lessons learned, the method and the cooperation framework; and Project journal, retracing the milestones reached, the observations made and the structuring decisions taken. Match Europe is used as the editorial identity, while the existing EURES Beta technical foundations are kept in place.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'The project becomes more readable and more transparent.',
            ),
            pgettext_lazy(
                "project journal",
                'Partners can now rely on a shared reference point to present the experiment.',
            ),
            pgettext_lazy(
                "project journal",
                'The project’s developments and trajectory can be followed more easily.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Update the journal regularly, consolidate published data and prepare the co-design of the pilot with the three public employment services.',
        ),
    },
    {
        "id": 'entry-2026-07-15',
        "datetime": '2026-07-15',
        'date': pgettext_lazy("project journal", 'July 15, 2026'),
        'title': pgettext_lazy("project journal", 'Trust becomes the main issue'),
        'observed': pgettext_lazy(
            "project journal",
            'The experiment confirms that it is possible to convince employers, collect their needs, identify candidates, qualify profiles, produce matching proposals and organise first introductions. The main obstacle therefore no longer lies in the feasibility of matching itself. However, a significant share of candidates still hesitate to respond when they do not immediately recognise the institutional origin of the service or the framework in which their data is used.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Evolve Match Europe towards an introduction service more clearly embodied by public employment services and their local relays. The strategy is to build an environment of trust before intensifying recruitment campaigns.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal",
                'Presenting the service through recognised professionals becomes a priority.',
            ),
            pgettext_lazy(
                "project journal",
                'Candidate consent and a clear institutional identity become central.',
            ),
            pgettext_lazy(
                "project journal",
                'Well-managed contact channels and human support become key components of the service.',
            ),
            pgettext_lazy(
                "project journal",
                'The gradual involvement of local agencies and the creation of a pool of around 300 informed and qualified candidates become structuring goals.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Co-design with French, Walloon and Luxembourg public employment services the conditions for a pilot across the three sides.',
        ),
    },
    {
        "id": 'entry-2026-07-01',
        "datetime": '2026-07-01',
        'date': pgettext_lazy("project journal", 'June-July 2026'),
        'title': pgettext_lazy("project journal", 'Test contact channels'),
        'observed': pgettext_lazy(
            "project journal",
            'Being able to identify a relevant candidate does not guarantee that the person will respond to outreach. Emails or messages coming from a service that is still little known may be ignored or may trigger mistrust.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Study more direct communication channels, including WhatsApp Business, starting with a limited manual use. This channel must remain governed by clear rules on consent, sender identity, authorised staff, exchanged information, message retention, traceability and the prohibition on using personal accounts.',
        ),
        'changed': pgettext_lazy(
            "project journal",
            'Initial contact is now treated as a product component in its own right, not as a secondary step after matching.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Test the most effective channels while reinforcing the service’s institutional and reassuring character.',
        ),
    },
    {
        "id": 'entry-2026-06-20',
        "datetime": '2026-06-20',
        'date': pgettext_lazy("project journal", 'June 2026'),
        'title': pgettext_lazy(
            "project journal", 'Build explainable and supervised matching'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'A simple match based on a job title is not enough to suggest a candidate to an employer. Relevance depends on several dimensions: occupation and experience, skills, languages, mobility, availability, working conditions, pay, as well as required qualifications or authorisations.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Build a matching engine based on objective and understandable rules. Each proposal must be explainable through the criteria that led to the suggested match. The final decision remains subject to human validation before any introduction takes place.',
        ),
        'changed': pgettext_lazy(
            "project journal",
            'The score is not an automatic decision. It becomes a decision-support tool used to compare profiles, understand their strengths and limits, and prepare a more effective human intervention.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Gradually enrich the model, especially through a better account of key skills, while assessing the risks of bias.',
        ),
    },
    {
        "id": 'entry-2026-06-15',
        "datetime": '2026-06-15',
        'date': pgettext_lazy("project journal", 'June 2026'),
        'title': pgettext_lazy(
            "project journal", 'Put a first operational version online'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'The initial collection tools made it possible to start quickly, but they were becoming insufficient to handle the growing number of profiles, needs and matching proposals. The service also needed to better address data protection, security, traceability, compliance, and the follow-up of decisions and exchanges.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Develop a first operational version of EURES Beta including a dedicated candidate entry point, a dedicated employer entry point, a statistics page, an administration space, an automated matching engine, manual validation before any transmission to an employer, and traceability of proposals and responses.',
        ),
        'changed': pgettext_lazy(
            "project journal",
            'The project no longer relies only on scattered manual processing. It now has an online service capable of structuring data, producing matching proposals and recording the main steps of the introduction process.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Test how the service is used, improve the forms and make the matching criteria more precise and more explainable.',
        ),
    },
    {
        "id": 'entry-2026-06-05',
        "datetime": '2026-06-05',
        'date': pgettext_lazy("project journal", 'Early June 2026'),
        'title': pgettext_lazy("project journal", 'Obtain the first field results'),
        'observed': pgettext_lazy(
            "project journal",
            'Within two weeks of experimentation with employers in Luxembourg: 2 employers took part; 5 recruitment needs were collected; 158 candidates were contacted; 35 profiles were obtained; 22 matching proposals were produced; and first interviews were initiated. These results show that it is possible to mobilise employers, identify candidates and produce matches within short timeframes.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Continue the experiment and transform the initial concierge-style mode into a more structured and traceable service.',
        ),
        'changed': [
            pgettext_lazy(
                "project journal", 'The project now has its first concrete results.'
            ),
            pgettext_lazy(
                "project journal",
                'The hypothesis of a cross-border introduction service is credible enough to justify developing a first operational tool.',
            ),
        ],
        'next': pgettext_lazy(
            "project journal",
            'Create an environment capable of collecting information, automating part of the matching process and preserving human validation.',
        ),
    },
    {
        "id": 'entry-2026-05-15',
        "datetime": '2026-05-15',
        'date': pgettext_lazy("project journal", 'May 2026'),
        'title': pgettext_lazy("project journal", 'Launch a first matching experiment'),
        'observed': pgettext_lazy(
            "project journal",
            'To understand the real conditions of cross-border introductions, it was necessary to move beyond purely theoretical reflection. A first experiment was therefore launched around the needs of employers in Luxembourg and candidates who might work in Luxembourg. The first targeted occupations notably concerned cleaning and maintenance, before a gradual opening to other sectors.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Test the service in a concierge-style mode: collect employer needs directly, identify potential candidates, contact them, qualify their interest and constraints, analyse possible matches and propose the most relevant introductions.',
        ),
        'changed': pgettext_lazy(
            "project journal",
            'The service is assessed on real situations and not only on the theoretical quality of an algorithm. Each exchange helps identify the information that is actually useful for matching and the difficulties faced by users.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Structure the collected data and formalise the first matching criteria.',
        ),
    },
    {
        "id": 'entry-2026-04-20',
        "datetime": '2026-04-20',
        'date': pgettext_lazy("project journal", 'April 2026'),
        'title': pgettext_lazy("project journal", "Choose the Startup d'Etat approach"),
        'observed': pgettext_lazy(
            "project journal",
            'The problem to be solved is complex and involves several administrations, countries, information systems and categories of users. In this context, defining a complete solution in advance would create a significant risk: building a long and costly service before verifying its real usefulness.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            "Apply the principles of the Startup d'Etat approach: start from user needs, work with a small team, test quickly, progress through iterations, measure impact, and keep the possibility of adjusting or stopping a hypothesis that does not work.",
        ),
        'changed': pgettext_lazy(
            "project journal",
            'Partners are not asked to validate a fixed specification. They are invited to contribute to a gradual experiment by providing access to users, useful data, professionals and existing schemes.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Build a first version of the candidate and employer journeys that is simple enough to be tested in the field.',
        ),
    },
    {
        "id": 'entry-2026-04-15',
        "datetime": '2026-04-15',
        'date': pgettext_lazy("project journal", 'April 15, 2026'),
        'title': pgettext_lazy(
            "project journal", 'Connect the experiment with European workstreams'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'Discussions with the EURES coordination team at France Travail confirmed several usability difficulties with the EURES portal, as well as an articulation with Europass that remains insufficient. They also made it possible to identify European work already under way around three priorities: a more personalised service, a mobile application and a shared dashboard.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            'Position the experiment as a concrete and complementary contribution to reflections already under way at European level. The project must demonstrate, through real use, what a simpler, more personalised and results-driven approach can bring.',
        ),
        'changed': pgettext_lazy(
            "project journal",
            'The experiment is conceived as a learning ground that can feed broader work on the evolution of EURES, without waiting for a complete transformation of European tools.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Gain access to the useful environments and resources, then prepare a first testable journey with real candidates and real employers.',
        ),
    },
    {
        "id": 'entry-2026-04-01',
        "datetime": '2026-04-01',
        'date': pgettext_lazy("project journal", 'April 2026'),
        'title': pgettext_lazy(
            "project journal", 'Understand the limits of the current system'
        ),
        'observed': pgettext_lazy(
            "project journal",
            'Initial discussions with cross-border employment stakeholders helped clarify how the labour market currently works in the Greater Region. Several limits were identified: tools remain largely organised by country; navigating between vacancies can lead to multiple redirects; available candidate profiles are sometimes only partially usable or anonymised; existing services do not always support quick and personalised introductions; and the various actors hold information and resources that remain difficult to mobilise within a single journey.',
        ),
        'decided': pgettext_lazy(
            "project journal",
            "Test a more direct approach focused on a concrete problem: better connect candidates and employers within the same cross-border economic area. The project adopts an approach inspired by Startup d'Etat: start from the field, experiment quickly and measure the results obtained.",
        ),
        'changed': pgettext_lazy(
            "project journal",
            'The project does not seek first to redesign the entire EURES system. It aims to test a limited solution that can be used quickly and then adjust it on the basis of feedback from candidates, employers and employment professionals.',
        ),
        'next': pgettext_lazy(
            "project journal",
            'Define a first use case and identify the partners who may contribute to the experiment.',
        ),
    },
]

for entry in ENTRIES:
    if isinstance(entry["changed"], list):
        entry["changed_items"] = entry["changed"]
