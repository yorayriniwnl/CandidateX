"""Cross-source explanations: separate declarations, observations, and attribution."""
import re
from datetime import datetime, timezone

from cci.intake.canonicalizer import classify_url
from cci.live.claims import build_academic_records, build_claim_ledger

SKILL_ALIASES = {'nextjs': 'nextjs', 'reactjs': 'react', 'html5': 'html', 'css3': 'css',
    'tailwindcss': 'tailwindcss', 'golang': 'go', 'scikitlearn': 'scikitlearn', 'cicd': 'cicd'}


def normalize_skill(skill):
    value = re.sub(r'[^a-z0-9+#]', '', skill.lower())
    return SKILL_ALIASES.get(value, value)


def text_mentions(text, value):
    return bool(value and re.search(r'(?<![\w])' + re.escape(value) + r'(?![\w])', text, re.I))


def build_report(intake, sources):
    learning = {normalize_skill(s) for s in intake.resume_review.learning_skills}
    skills = []
    for skill in intake.manifest.claimed_skills:
        matches, mentions = [], []
        for source in sources:
            for technology in source.get('repository_review', {}).get('technologies', []):
                if normalize_skill(technology['name']) == normalize_skill(skill):
                    matches.append({**technology, 'repository_url': source['url'],
                                    'attribution_observed': source.get('ownership_score', 0) > 0})
            if source.get('status') == 'observed' and text_mentions(source.get('excerpt', ''), skill):
                mentions.append(source['url'])
        attributed = any(m['attribution_observed'] for m in matches)
        skills.append({'skill': skill, 'learning': normalize_skill(skill) in learning,
            'status': 'repository_support' if attributed else 'repository_only' if matches else 'public_mention_only' if mentions else 'not_observed',
            'evidence': matches[:12], 'evidence_count': len(matches), 'public_mentions': mentions,
            'explanation': ('Matching source files or dependency/configuration declarations were inspected. This supports a technical follow-up, not mastery.' if attributed else
                            'Technology appears in a repository, but candidate attribution was not established.' if matches else
                            'Public page text mentions this skill; self-published mentions do not establish capability.' if mentions else
                            'No matching technology was observed in the bounded scan. This is not a claim that the candidate lacks the skill.')})

    credentials = []
    credential_sources = [s for s in sources if s.get('kind') == 'credential' or classify_url(s['url']) == 'credential']
    for claim in intake.resume_review.sections.get('certifications', []):
        # Topic overlap associates review candidates only, never authenticates a credential.
        tokens = [t.lower() for t in re.findall(r'[A-Za-z]{4,}', claim)
                  if t.lower() not in {'certificate', 'certified', 'certification', 'course', 'completion', 'with', 'from'}]
        matches = []
        for source in credential_sources:
            if source['status'] != 'observed':
                continue
            text = f"{source.get('title', '')} {source.get('excerpt', '')}"
            overlap = [t for t in tokens if text_mentions(text, t)]
            if len(overlap) >= min(2, max(1, len(tokens))) and tokens:
                matches.append({'url': source['url'], 'title': source.get('title', ''),
                    'matched_terms': overlap, 'candidate_name_present': intake.manifest.display_name != 'Unknown Candidate'
                    and text_mentions(text, intake.manifest.display_name)})
        credentials.append({'claim': claim, 'status': 'possible_public_match' if matches else 'unverified',
            'matching_pages': matches, 'explanation': 'Public text matching is not issuer authentication. Confirm recipient, credential ID, issuer, issue/expiry dates and revocation status with the issuer.'})

    projects = []
    for project in intake.manifest.project_claims:
        text = f"{project.get('title', '')} {project.get('description', '')}"
        refs = [s['url'] for s in sources if s['url'].removeprefix('https://').removeprefix('http://').lower() in text.lower()]
        projects.append({**project, 'source_urls': refs, 'status': 'linked_sources' if refs else 'declaration_only',
                         'explanation': 'Links connect this project to acquisition receipts; impact, performance and contribution claims still require separate verification.'})
    sections = intake.resume_review.sections
    numeric_claims = [line for lines in sections.values() for line in lines if re.search(r'\d+(?:\.\d+)?\s*%|\b\d+[+-]?\s+(?:users|tests|projects|applications|points)\b', line, re.I)]
    actions = []
    if not any(s.get('ownership_score', 0) > 0 for s in sources):
        actions.append('Confirm the candidate-declared GitHub account and review contribution attribution.')
    if any(s['status'] != 'observed' for s in sources):
        actions.append('Review unavailable or unscanned sources; run again with a smaller selected set where needed.')
    if credentials:
        actions.append('Confirm certificates with their issuer, including recipient, credential ID and dates.')
    actions.append('Use the skill evidence paths and project claims to request a walkthrough of the candidate’s actual contribution.')
    claims = build_claim_ledger(intake)
    academic_records = build_academic_records(intake)
    source_statuses = {}
    source_kinds = {}
    discovered_links = []
    seen_discovered = set()
    for source in sources:
        status = source.get('status', 'unknown')
        kind = source.get('kind') or classify_url(source.get('url', ''))
        source_statuses[status] = source_statuses.get(status, 0) + 1
        source_kinds[kind] = source_kinds.get(kind, 0) + 1
        for discovered in source.get('discovered_links', []):
            url = discovered.get('url')
            if url and url not in seen_discovered:
                seen_discovered.add(url)
                discovered_links.append(discovered)

    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'skills': skills, 'credentials': credentials,
        'projects': projects, 'experience': [{'claim': line, 'status': 'self_reported'} for line in sections.get('experience', [])],
        'education': [{'claim': line, 'status': 'self_reported'} for line in sections.get('education', [])],
        'academic_records': academic_records, 'claims': claims,
        'achievements': [{'claim': line, 'status': 'self_reported'} for line in sections.get('achievements', [])],
        'quantified_claims_to_verify': list(dict.fromkeys(numeric_claims))[:30], 'next_steps': actions,
        'discovered_links': discovered_links,
        'source_coverage': {'by_status': source_statuses, 'by_kind': source_kinds,
                            'discovered_links': len(discovered_links)},
        'coverage': {'supplied_sources': len(sources), 'observed_sources': sum(s['status'] == 'observed' for s in sources),
                     'skills_declared': len(skills), 'skills_with_repository_matches': sum(bool(s['evidence']) for s in skills),
                     'credential_claims': len(credentials)},
        'method': 'Deterministic document extraction, bounded public acquisition, and exact technology matching. Resume claims remain declarations unless separate evidence supports them; public-page link discovery is retained for follow-up analysis.'}
