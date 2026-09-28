"""Cross-source explanations: separate declarations, observations, and attribution."""
import re
from datetime import datetime, timezone

from cci.intake.canonicalizer import classify_url

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
    credential_sources = [s for s in sources if s.get('kind') == 'credential' or classify_url(s['url']) == 'credential' or s.get('inferred_kind') == 'credential']
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
        unverified_storage = [
            r for r in refs
            if any(s['url'] == r and (s.get('kind') == 'cloud_storage' or classify_url(s['url']) == 'cloud_storage')
                   and s.get('inferred_kind') != 'project'
                   and not s.get('files')
                   and s.get('verification') != 'cloud_file_verified'
                   for s in sources)
        ]
        fetched_storage = [s for s in sources if s['url'] in refs and (s.get('files') or s.get('verification') == 'cloud_file_verified')]
        if unverified_storage and not any(s.get('repository_review') for s in sources if s['url'] in refs):
            projects.append({
                **project,
                'source_urls': refs,
                'status': 'linked_unverified_storage',
                'explanation': 'Supplied link points to cloud storage (e.g. Google Drive/OneDrive). File contents and purpose have not been verified as a project file; separate technical review is required.',
            })
        else:
            explanation = (
                f"Cloud files fetched and inspected ({sum(len(s.get('files', [])) for s in fetched_storage)} files). Code and project artifacts observed."
                if fetched_storage else
                'Links connect this project to acquisition receipts; impact, performance and contribution claims still require separate verification.'
            )
            projects.append({
                **project,
                'source_urls': refs,
                'status': 'linked_sources' if refs else 'declaration_only',
                'explanation': explanation,
            })
    portfolios = []
    portfolio_sources = [
        s for s in sources
        if s.get('kind') == 'portfolio'
        or classify_url(s.get('url', '')) == 'portfolio'
        or s.get('inferred_kind') == 'portfolio'
        or s.get('url') in getattr(intake.manifest, 'portfolio_urls', [])
    ]
    for p_url in getattr(intake.manifest, 'portfolio_urls', []):
        source_match = next((s for s in portfolio_sources if s['url'] == p_url), None)
        status = source_match.get('status') if source_match else 'unverified'
        title = source_match.get('title') if source_match else ''
        excerpt = source_match.get('excerpt') if source_match else ''
        techs = source_match.get('technologies', []) if source_match else []
        explanation = (
            f"Observed live portfolio website ({title or p_url}). Extracted showcase artifacts and verified online presence."
            if status == 'observed' else
            f"Candidate-declared portfolio website ({p_url}); not verified or reachable during scan."
        )
        portfolios.append({
            'url': p_url,
            'title': title or 'Portfolio Website',
            'status': status,
            'technologies': techs,
            'excerpt': excerpt[:500] if excerpt else '',
            'explanation': explanation,
        })

    sections = intake.resume_review.sections
    numeric_claims = [line for lines in sections.values() for line in lines if re.search(r'\d+(?:\.\d+)?\s*%|\b\d+[+-]?\s+(?:users|tests|projects|applications|points)\b', line, re.I)]
    actions = []
    if not any(s.get('ownership_score', 0) > 0 for s in sources):
        actions.append('Confirm the candidate-declared GitHub account and review contribution attribution.')
    if any(s['status'] != 'observed' for s in sources):
        actions.append('Review unavailable or unscanned sources; run again with a smaller selected set where needed.')
    if credentials:
        actions.append('Confirm certificates with their issuer, including recipient, credential ID and dates.')
    if portfolios:
        actions.append('Inspect candidate portfolio website and live project demonstrations.')
    actions.append('Use the skill evidence paths and project claims to request a walkthrough of the candidate’s actual contribution.')
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'skills': skills, 'credentials': credentials,
        'portfolios': portfolios,
        'projects': projects, 'experience': [{'claim': line, 'status': 'self_reported'} for line in sections.get('experience', [])],
        'education': [{'claim': line, 'status': 'self_reported'} for line in sections.get('education', [])],
        'achievements': [{'claim': line, 'status': 'self_reported'} for line in sections.get('achievements', [])],
        'quantified_claims_to_verify': list(dict.fromkeys(numeric_claims))[:30], 'next_steps': actions,
        'coverage': {'supplied_sources': len(sources), 'observed_sources': sum(s['status'] == 'observed' for s in sources),
                     'skills_declared': len(skills), 'skills_with_repository_matches': sum(bool(s['evidence']) for s in skills),
                     'credential_claims': len(credentials)},
        'method': 'Deterministic document extraction, bounded public acquisition, and exact technology matching. No generated biography or inferred employment verification.'}
