#!/usr/bin/env python3
"""Build the existing static URLs from data and templates; Python 3.12, no dependencies."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import html
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
NAVIGATION = [('index', 'Home'), ('research', 'Research'), ('people', 'People'),
              ('publications', 'Publications'), ('news', 'News'),
              ('gallery', 'Gallery'), ('contact', 'Contact')]
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December')
TOKEN = re.compile(r'{{\s*([a-z_0-9]+)\s*}}')


def load(name):
    return json.loads((ROOT / 'data' / f'{name}.json').read_text(encoding='utf-8'))


def escape(value):
    return html.escape(str(value), quote=True)


def render(template, values):
    def replace(match):
        key = match[1]
        if key not in values:
            raise ValueError(f'Unknown template field: {key}')
        return str(values[key])
    return TOKEN.sub(replace, template)


def local_image(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT / 'assets' / 'images') or not path.is_file():
        raise ValueError(f'Missing or invalid image path: {value}')


def validate(publications, gallery, news, references):
    numbers, keys, dois = set(), set(), set()
    for paper in publications:
        number = paper['number']
        if type(number) is not int or number < 1 or number in numbers:
            raise ValueError(f'Invalid or duplicate publication number: {number}')
        numbers.add(number)
        key = paper['key']
        if not re.fullmatch(r'[A-Za-z0-9_:-]+', key) or key in keys:
            raise ValueError(f'Invalid or duplicate BibTeX key: {key}')
        keys.add(key)
        for field in ('title', 'journal', 'authors'):
            if not paper.get(field):
                raise ValueError(f'Paper {number}: missing {field}')
        for author in paper['authors']:
            if not author.get('name') or re.search(r'[{}\\]', author['name']):
                raise ValueError(f'Paper {number}: invalid author')
        year = paper.get('year')
        if year is not None and (type(year) is not int or not 1900 <= year <= 2200):
            raise ValueError(f'Paper {number}: invalid year')
        if year is None and paper.get('status') != 'Accepted':
            raise ValueError(f'Paper {number}: year required unless Accepted')
        doi = paper.get('doi')
        if doi:
            if not re.fullmatch(r'10\.\d{4,9}/[^\s<>"{}]+', doi) or doi.casefold() in dois:
                raise ValueError(f'Paper {number}: invalid or duplicate DOI')
            dois.add(doi.casefold())
    for photo in gallery:
        date.fromisoformat(photo['date'])
        local_image(photo['image'])
        if photo.get('original'):
            local_image(photo['original'])
        if not photo['alt'].strip() or not photo['caption'].strip():
            raise ValueError('Gallery images need alt text and a caption')
        if any(type(photo[k]) is not int or photo[k] < 1 for k in ('width', 'height')):
            raise ValueError('Gallery width and height must be positive integers')
    for item in news:
        date.fromisoformat(item['date'])
        if not all(item.get(k) for k in ('title', 'text', 'category')):
            raise ValueError('News needs title, text and category')
    for ref in references:
        if ref['number'] not in numbers:
            raise ValueError(f'Unknown representative paper: {ref["number"]}')


def navigation(page):
    current = 'people' if page == 'moon-young-yang' else page
    links = []
    for slug, label in NAVIGATION:
        active = ' class="active" aria-current="page"' if current == slug else ''
        links.append(f'<a{active} href="{slug}.html">{label}</a>')
    return '<nav id="primary-navigation" class="nav-links" aria-label="Main navigation">\n' + '\n'.join(links) + '\n</nav>'


def render_gallery(items):
    cards = []
    for item in sorted(items, key=lambda p: p['date'], reverse=True):
        day = date.fromisoformat(item['date'])
        label = f'{MONTHS[day.month - 1]} {day.day}, {day.year}'
        cards.append(f'''<figure class="gallery-card">
  <a aria-label="View photo: {escape(item['caption'])}" href="{escape(item.get('original', item['image']))}">
    <img alt="{escape(item['alt'])}" loading="lazy" decoding="async" src="{escape(item['image'])}" width="{item['width']}" height="{item['height']}"/>
  </a>
  <figcaption><time datetime="{item['date']}">{label}</time><p>{escape(item['caption'])}</p></figcaption>
</figure>''')
    return '\n'.join(cards)


def citation(paper):
    text = f'<em>{escape(paper["journal"])}</em>'
    if paper.get('status') == 'Accepted':
        return text + ', Accepted.'
    text += f', {paper["year"]}'
    if paper.get('volume'):
        text += ', ' + escape(paper['volume'])
        if paper.get('issue'):
            text += '(' + escape(paper['issue']) + ')'
    if paper.get('pages'):
        text += ':' + escape(paper['pages'])
    return text + '.'


def render_paper(paper):
    authors = []
    for author in paper['authors']:
        name = escape(author['name'])
        if author['name'] == 'Moon Young Yang':
            name = '<strong>' + name + '</strong>'
        marks = ('†' if author.get('equal') else '') + ('*' if author.get('corresponding') else '')
        authors.append(name + (f'<sup>{marks}</sup>' if marks else ''))
    title = escape(paper['title'])
    if paper.get('doi'):
        title = f'<a class="title-link" href="https://doi.org/{escape(paper["doi"])}" rel="noopener" target="_blank">{title}</a>'
    note = f'<div class="pub-note">{escape(paper["note"])}</div>' if paper.get('note') else ''
    return f'''<article class="pub" id="paper-{paper['number']}">
  <div class="pub-number">({paper['number']})</div>
  <div class="pub-body">
    <div class="pub-title">{title}</div>
    <div class="pub-authors">{', '.join(authors)}</div>
    <div class="pub-meta">{citation(paper)}</div>
{note}
  </div>
</article>'''


def render_publications(papers):
    groups = {}
    for paper in sorted(papers, key=lambda p: p['number'], reverse=True):
        group = 'Accepted' if paper.get('status') == 'Accepted' else str(paper['year'])
        groups.setdefault(group, []).append(paper)
    order = sorted(groups, key=lambda key: (key == 'Accepted', int(key) if key.isdigit() else 0), reverse=True)
    return '\n'.join(f'<section class="year-block">\n<h2 class="year-title">{key}</h2>\n<div class="pub-list">\n'
                     + '\n'.join(render_paper(p) for p in groups[key]) + '\n</div>\n</section>' for key in order)


def bibtex_escape(value):
    # Literal braces/backslashes from trusted data are escaped; unicode is retained.
    return str(value).translate(str.maketrans({'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}',
                                              '&': r'\&', '%': r'\%', '_': r'\_', '#': r'\#', '$': r'\$'}))


def render_bibtex(papers):
    entries = []
    for paper in sorted(papers, key=lambda p: p['number'], reverse=True):
        fields = {'title': paper['title'], 'author': ' and '.join(a['name'] for a in paper['authors']),
                  'journal': paper['journal']}
        for source, target in [('year', 'year'), ('volume', 'volume'), ('issue', 'number'), ('pages', 'pages'), ('doi', 'doi')]:
            if paper.get(source) is not None:
                fields[target] = paper[source]
        if paper.get('status') == 'Accepted':
            fields['note'] = 'Accepted'
        elif paper.get('note'):
            fields['note'] = paper['note']
        fields['publication_no'] = paper['number']
        for flag, target in [('equal', 'equal_contribution'), ('corresponding', 'corresponding_author')]:
            names = [a['name'] for a in paper['authors'] if a.get(flag)]
            if names:
                fields[target] = ' and '.join(names)
        lines = []
        for key, value in fields.items():
            value = bibtex_escape(value)
            if key == 'title':
                value = '{' + value + '}'
            lines.append(f'  {key} = {{{value}}}')
        entries.append('@article{' + paper['key'] + ',\n' + ',\n'.join(lines) + '\n}')
    return '\n\n'.join(entries) + '\n'


def render_news(items, preview=False):
    output = []
    for item in sorted(items, key=lambda i: i['date'], reverse=True)[:1 if preview else None]:
        day = date.fromisoformat(item['date'])
        meta = f'{MONTHS[day.month - 1]} {day.year} · {escape(item["category"])}'
        content = f'<div class="news-meta">{meta}</div>\n<h{3 if preview else 2}>{escape(item["title"])}</h{3 if preview else 2}>\n<p>{escape(item["text"])}</p>'
        output.append(f'<a class="news-preview" href="news.html">{content}</a>' if preview else f'<article class="news-entry">{content}</article>')
    return '\n'.join(output)


def build_outputs():
    papers, gallery, news, refs, site = (load(n) for n in ('publications', 'gallery', 'news', 'research-papers', 'site'))
    validate(papers, gallery, news, refs)
    # Page styles first, common styles second: matches the original cascade order.
    css_files = ['people.css', 'publications.css', 'moon-young-yang.css', 'site.css']
    css = '\n'.join((ROOT / 'src/styles' / name).read_text(encoding='utf-8') for name in css_files)
    js = (ROOT / 'src/site.js').read_text(encoding='utf-8')
    css_path = f'assets/site.{hashlib.sha256(css.encode()).hexdigest()[:12]}.css'
    js_path = f'assets/site.{hashlib.sha256(js.encode()).hexdigest()[:12]}.js'
    values = {key: escape(value) for key, value in site.items()}
    values.update(stylesheets=f'<link href="{css_path}" rel="stylesheet"/>',
                  scripts=f'<script src="{js_path}" defer></script>', gallery=render_gallery(gallery),
                  publications=render_publications(papers), news=render_news(news), latest_news=render_news(news, True))
    by_number = {p['number']: p for p in papers}
    for ref in refs:
        paper = by_number[ref['number']]
        # Research keeps its editorial short title, and links to the canonical numbered record.
        label = escape(ref['journal_label']) + (f' ({paper["year"]})' if paper.get('year') else ' (Accepted)')
        values[f'research_paper_{paper["number"]}'] = f'<div class="pubitem"><a href="publications.html#paper-{paper["number"]}"><strong>{escape(ref["title"])}</strong></a><span>{label}</span></div>'
    outputs = {css_path: css.encode(), js_path: js.encode(), 'papers.bib': render_bibtex(papers).encode(), '.nojekyll': b''}
    for template in sorted((ROOT / 'src/pages').glob('*.html')):
        context = {**values, 'navigation': navigation(template.stem)}
        context['header'] = render((ROOT / 'src/partials/header.html').read_text(), context)
        context['footer'] = render((ROOT / 'src/partials/footer.html').read_text(), context)
        result = render(template.read_text(encoding='utf-8'), context)
        outputs[template.name] = result.encode()
    return outputs


def write_outputs(output, check=False):
    outputs = build_outputs()
    if check:
        stale = [name for name, content in outputs.items()
                 if not (output / name).is_file() or (output / name).read_bytes() != content]
        stale += [str(p.relative_to(output)) for p in (output / 'assets').glob('site.*.*')
                  if re.fullmatch(r'site\.[0-9a-f]{12}\.(css|js)', p.name) and str(p.relative_to(output)) not in outputs]
        if stale:
            raise ValueError('Generated files are stale. Run python3 scripts/build.py: ' + ', '.join(stale))
        print('Generated files match data, templates and asset hashes.')
        return
    output.mkdir(parents=True, exist_ok=True)
    if output.resolve() != ROOT:
        # Copy only deployable image files; source, tests and historic styles stay out of the artifact.
        shutil.copytree(ROOT / 'assets/images', output / 'assets/images', dirs_exist_ok=True)
    for name, content in outputs.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for path in (output / 'assets').glob('site.*.*'):
        if re.fullmatch(r'site\.[0-9a-f]{12}\.(css|js)', path.name) and str(path.relative_to(output)) not in outputs:
            path.unlink()
    print(f'Built {len(outputs)} files in {output}; {len(load("publications"))} publications.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT, help='Default: refresh tracked root HTML; use _site for a deployment artifact')
    parser.add_argument('--check', action='store_true', help='Fail if generated files are out of date; do not write')
    args = parser.parse_args()
    try:
        write_outputs(args.output.resolve(), args.check)
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Build failed: {exc}\n')


if __name__ == '__main__':
    main()
