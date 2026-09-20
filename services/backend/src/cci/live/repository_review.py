"""Explain inspected repository contents without executing candidate code."""
import json
import re
import tomllib
from collections import Counter
from pathlib import Path
from urllib.parse import quote
from cci.analyzers.repository.indexer import categorize_file

LANGUAGES = {'.py': 'Python', '.ts': 'TypeScript', '.tsx': 'TypeScript', '.js': 'JavaScript',
             '.jsx': 'JavaScript', '.java': 'Java', '.go': 'Go', '.rs': 'Rust', '.sql': 'SQL',
             '.html': 'HTML', '.css': 'CSS', '.cpp': 'C++', '.c': 'C', '.cs': 'C#', '.rb': 'Ruby',
             '.php': 'PHP', '.swift': 'Swift', '.kt': 'Kotlin', '.ipynb': 'Jupyter'}
ALIASES = {'react': 'React', 'next': 'Next.js', 'fastapi': 'FastAPI', 'flask': 'Flask',
           'django': 'Django', 'tailwindcss': 'Tailwind CSS', 'typescript': 'TypeScript',
           'scikit-learn': 'Scikit-Learn', 'opencv-python': 'OpenCV', 'pytest': 'Pytest',
           'vitest': 'Vitest', '@playwright/test': 'Playwright', 'three': 'Three.js',
           'framer-motion': 'Framer Motion', 'langchain': 'LangChain', 'express': 'Express',
           'torch': 'PyTorch', 'tensorflow': 'TensorFlow', 'numpy': 'NumPy', 'pandas': 'Pandas'}


def dependency_names(path, text):
    try:
        if path.endswith('package.json'):
            data = json.loads(text)
            return [(name, str(version)[:100]) for group in ('dependencies', 'devDependencies', 'peerDependencies')
                    for name, version in data.get(group, {}).items()][:200]
        if path.endswith('pyproject.toml'):
            data = tomllib.loads(text).get('project', {})
            entries = data.get('dependencies', []) + [entry for group in data.get('optional-dependencies', {}).values() for entry in group]
        elif re.search(r'requirements[^/]*\.txt$', path):
            entries = text.splitlines()
        else:
            return []
        return [(match.group(1), line[:100]) for line in entries if isinstance(line, str)
                and (match := re.match(r'^\s*([\w.-]+)(?:\[|[<=>!~;\s]|$)', line))]
    except (ValueError, TypeError, AttributeError):
        return []


def review_repository(root, artifacts, url, sha, metadata):
    languages, categories = Counter(), Counter()
    technologies, dependencies, signals = [], [], {}
    readme = ''

    def add_technology(name, path, basis):
        if len(technologies) < 350 and sum(t['name'] == name for t in technologies) < 5:
            technologies.append({'name': name, 'path': path, 'basis': basis,
                'url': f'{url}/blob/{sha}/{quote(path, safe="/")}'})

    for artifact in artifacts:
        path = artifact.relative_path
        suffix = Path(path).suffix.lower()
        category = categorize_file(path)
        categories[category] += 1
        if suffix in LANGUAGES:
            languages[LANGUAGES[suffix]] += 1
            if category not in {'docs', 'manifests'}:
                add_technology(LANGUAGES[suffix], path, 'source_file_extension')
        text = Path(root, path).read_text(encoding='utf-8', errors='replace')
        for name, version in dependency_names(path, text):
            if len(dependencies) < 200:
                dependencies.append({'name': name, 'version': version, 'path': path})
            add_technology(ALIASES.get(name.lower(), name), path, 'declared_dependency')
        if path.lower().endswith('package.json'):
            add_technology('Node.js', path, 'package_manifest')
        if 'dockerfile' in path.lower() or re.search(r'(?:docker-)?compose\.ya?ml$', path, re.I):
            add_technology('Docker', path, 'container_configuration')
        if path.startswith('.github/workflows/'):
            add_technology('CI/CD', path, 'workflow_configuration')
        if Path(path).name.lower().startswith('readme') and not readme:
            readme = text[:1600]
        for key, match in {
            'tests': category == 'tests', 'ci': category == 'ci',
            'infrastructure': category == 'infra', 'database': category == 'database',
            'documentation': category == 'docs', 'api_schema': category == 'openapi',
        }.items():
            if match:
                signals.setdefault(key, []).append(path)
    return {'description': metadata.get('description'), 'primary_language': metadata.get('language'),
        'stars': metadata.get('stargazers_count', 0), 'forks': metadata.get('forks_count', 0),
        'open_issues': metadata.get('open_issues_count', 0), 'is_fork': bool(metadata.get('fork')),
        'archived': bool(metadata.get('archived')), 'license': (metadata.get('license') or {}).get('spdx_id'),
        'topics': metadata.get('topics', [])[:30], 'created_at': metadata.get('created_at'),
        'pushed_at': metadata.get('pushed_at'), 'homepage': metadata.get('homepage'),
        'languages_by_inspected_file': dict(languages), 'file_categories': dict(categories),
        'dependencies': dependencies, 'technologies': technologies, 'readme_excerpt': readme,
        'engineering_signals': [{'name': key, 'status': 'files_observed' if signals.get(key) else 'not_observed_in_scan',
                                'paths': signals.get(key, [])[:12]} for key in
                               ('tests', 'ci', 'infrastructure', 'database', 'documentation', 'api_schema')],
        'limitations': ['Counts and missing signals refer only to inspected files.',
                       'Dependency declarations do not prove usage. Tests and workflows were not executed.',
                       'Stars, forks, and activity are context and never capability scores.']}
