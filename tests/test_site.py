import copy
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.references, self.stylesheets, self.scripts = set(), [], [], []
        self.inline_styles = False
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                raise ValueError(f'Duplicate ID: {attrs["id"]}')
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.references.append(attrs[key])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.stylesheets.append(attrs['href'])
        if tag == 'script':
            self.scripts.append(attrs.get('src'))
        if tag == 'style' or 'style' in attrs:
            self.inline_styles = True


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = build.build_outputs()
        cls.papers = build.load('publications')
        cls.pages = {name: Page(content.decode()) for name, content in cls.outputs.items() if name.endswith('.html')}

    def test_all_local_files_and_fragment_links_resolve(self):
        for name, page in self.pages.items():
            for reference in page.references:
                url = urlsplit(reference)
                if url.scheme or url.netloc:
                    continue
                target = unquote(url.path) or name
                self.assertTrue(target in self.outputs or (ROOT / target).is_file(), (name, reference))
                if url.fragment:
                    self.assertIn(target, self.pages, (name, reference))
                    self.assertIn(unquote(url.fragment), self.pages[target].ids, (name, reference))

    def test_css_image_paths_exist(self):
        css = next(content.decode() for name, content in self.outputs.items() if name.endswith('.css'))
        for reference in re.findall(r'url\([\s\'"]*([^\)\'\"]+)', css):
            self.assertTrue((ROOT / 'assets' / reference).is_file(), reference)

    def test_every_page_uses_same_content_addressed_assets(self):
        styles, scripts = set(), set()
        for name, page in self.pages.items():
            if name == 'join.html':
                continue
            self.assertFalse(page.inline_styles, name)
            self.assertEqual(len(page.stylesheets), 1)
            self.assertEqual(len(page.scripts), 1)
            styles.update(page.stylesheets)
            scripts.update(page.scripts)
        self.assertEqual(len(styles), 1)
        self.assertEqual(len(scripts), 1)
        for path in styles | scripts:
            digest = hashlib.sha256(self.outputs[path]).hexdigest()[:12]
            self.assertIn(f'.{digest}.', path)

    def test_publication_corrections_match_html_and_bibtex(self):
        papers = {paper['number']: paper for paper in self.papers}
        self.assertEqual(papers[60]['pages'], '2073–2093')
        self.assertIn('Mingyang Liu', [a['name'] for a in papers[62]['authors']])
        self.assertIsNone(papers[63]['year'])
        self.assertEqual(papers[63]['status'], 'Accepted')
        for paper in self.papers:
            fragment = build.render_paper(paper)
            self.assertIn(f'id="paper-{paper["number"]}"', fragment)
            bib = build.render_bibtex([paper])
            for author in paper['authors']:
                self.assertIn(build.bibtex_escape(author['name']), bib)
            if paper.get('doi'):
                self.assertIn(paper['doi'], bib)
            if paper.get('pages'):
                self.assertIn(paper['pages'], bib)
        self.assertNotIn('year =', build.render_bibtex([papers[63]]))
        self.assertIn('note = {Accepted}', build.render_bibtex([papers[63]]))
        self.assertEqual(len(self.papers), len(re.findall(r'@article\{', self.outputs['papers.bib'].decode())))

    def test_new_content_renders_without_editing_html(self):
        paper = copy.deepcopy(self.papers[0])
        paper.update(number=max(p['number'] for p in self.papers) + 1, key='newAcceptedPaper', doi=None, title='New <paper> & research')
        rendered = build.render_publications([paper, *self.papers])
        self.assertIn('New &lt;paper&gt; &amp; research', rendered)
        self.assertIn('Accepted', rendered)
        self.assertNotIn('href="https://doi.org/None', rendered)
        photo = copy.deepcopy(build.load('gallery')[0])
        photo.update(date='2027-01-02', caption='New <photo> & team')
        self.assertIn('January 2, 2027', build.render_gallery([photo]))
        self.assertIn('New &lt;photo&gt; &amp; team', build.render_gallery([photo]))
        news = build.load('news') + [{'date': '2027-01-01', 'category': 'Research', 'title': 'New result', 'text': 'A new paper.'}]
        self.assertIn('New result', build.render_news(news, True))
        self.assertNotIn('MCS Lab launches', build.render_news(news, True))
        self.assertIn('MCS Lab launches', build.render_news(news))

    def test_invalid_data_fails_before_generation(self):
        def validate(papers=None, gallery=None, references=None):
            build.validate(papers if papers is not None else self.papers,
                           gallery if gallery is not None else build.load('gallery'),
                           build.load('news'), references if references is not None else build.load('research-papers'))
        with self.assertRaisesRegex(ValueError, 'duplicate publication'):
            validate(papers=self.papers + [self.papers[0]])
        papers = copy.deepcopy(self.papers)
        papers[1]['year'] = None
        with self.assertRaisesRegex(ValueError, 'year required'):
            validate(papers=papers)
        photos = copy.deepcopy(build.load('gallery'))
        photos[0]['image'] = '../missing.jpg'
        with self.assertRaisesRegex(ValueError, 'image path'):
            validate(gallery=photos)
        with self.assertRaisesRegex(ValueError, 'representative paper'):
            validate(references=[{'number': -1}])

    def test_css_changes_invalidate_every_page_reference(self):
        original = Path.read_text
        def changed(path, *args, **kwargs):
            content = original(path, *args, **kwargs)
            return content + '\n/* changed stylesheet */\n' if path == ROOT / 'src/styles/site.css' else content
        with patch.object(Path, 'read_text', changed):
            modified = build.build_outputs()
        old_css = next(name for name in self.outputs if name.endswith('.css'))
        new_css = next(name for name in modified if name.endswith('.css'))
        self.assertNotEqual(old_css, new_css)
        for name, content in modified.items():
            if name.endswith('.html') and name != 'join.html':
                self.assertIn(new_css, content.decode())
                self.assertNotIn(old_css, content.decode())

    def test_repeatable_build_and_stale_output_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            build.write_outputs(output)
            before = {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
            build.write_outputs(output)
            after = {p.relative_to(output): p.read_bytes() for p in output.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            build.write_outputs(output, check=True)
            (output / 'index.html').write_text('stale')
            with self.assertRaisesRegex(ValueError, 'stale'):
                build.write_outputs(output, check=True)

    def test_header_footer_have_one_source_and_active_parent(self):
        headers, footers = set(), set()
        for name, content in self.outputs.items():
            if not name.endswith('.html') or name == 'join.html':
                continue
            text = content.decode()
            self.assertNotIn('{{', text)
            self.assertEqual(text.count('aria-current="page"'), 1)
            header = re.search(r'<header class="nav">.*?</header>', text, re.S).group()
            headers.add(re.sub(r' class="active" aria-current="page"', '', header))
            footers.add(re.search(r'<footer.*?</footer>', text, re.S).group())
        self.assertEqual(len(headers), 1)
        self.assertEqual(len(footers), 1)
        self.assertIn('aria-current="page" href="people.html"', self.outputs['moon-young-yang.html'].decode())


if __name__ == '__main__':
    unittest.main()
