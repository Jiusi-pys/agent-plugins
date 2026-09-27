"""Validate evidence bookkeeping; these checks cannot prove semantic correctness."""
from urllib.parse import urlsplit
from common import require_text, exact_coverage


def validate_profile(profile):
    if profile.get('mode', 'foreign') not in ('foreign', 'classical_chinese'):
        raise ValueError('Unknown translation mode')
    if profile.get('mode') == 'classical_chinese':
        from classical import validate_profile as validate_classical_profile
        validate_classical_profile(profile)
    if profile.get('language') != 'zh-Hans':
        raise ValueError('This workflow requires language=zh-Hans')
    for field in ('reader', 'style'):
        require_text(profile.get(field), field)
    if not isinstance(profile.get('glossary'), list):
        raise ValueError('Expected a glossary list')
    for term in profile['glossary']:
        require_text(term.get('source'), 'glossary source')
        require_text(term.get('target'), 'glossary target')
    bibliography = profile.get('bibliography', {})
    require_text(bibliography.get('title'), 'Chinese title')
    authors = bibliography.get('authors')
    if not isinstance(authors, list) or not authors:
        raise ValueError('Expected Chinese author names')
    for author in authors:
        require_text(author, 'author')
    require_text(bibliography.get('decision'), 'bibliography decision')
    status = bibliography.get('status')
    if status not in ('verified', 'provisional', 'user_supplied', 'original_sample'):
        raise ValueError('Bibliography search is not completed')
    sources = bibliography.get('sources')
    if not isinstance(sources, list) or (status == 'verified' and not sources):
        raise ValueError('Verified bibliography requires sources')
    for source in sources:
        if urlsplit(source.get('url', '')).scheme not in ('https', 'http'):
            raise ValueError('Expected an HTTP(S) bibliography source')
        for field in ('title', 'accessed', 'matched_on'):
            require_text(source.get(field), 'source ' + field)
    if status == 'user_supplied':
        require_text(bibliography.get('user_instruction'), 'user-provided names instruction')


def approved(report, coverage, fields):
    if report.get('verdict') != 'approved':
        raise ValueError('Review is not approved')
    exact_coverage(report.get('coverage'), coverage)
    findings = report.get('findings')
    if not isinstance(findings, list):
        raise ValueError('Review must include findings')
    for finding in findings:
        if not isinstance(finding, dict) or finding.get('status') != 'resolved':
            raise ValueError('Unresolved review findings')
        for field in ('id', 'evidence', 'resolution'):
            require_text(finding.get(field), 'resolved finding ' + field)
    for field in fields:
        require_text(report.get(field), 'review ' + field)
