# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime, date
from io import StringIO
from weakref import ref
from typing import TYPE_CHECKING, Optional
from abc import ABC, abstractmethod
import yaml
from markdown import Markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from jinja2 import Markup
from docutils.core import publish_parts

from blogme.constant import *


if TYPE_CHECKING:
    from blogme.builder import FileContext


class BaseParser(ABC):
    """
    parse file for specific format
    """
    def __init__(self, context: 'FileContext'):
        self._context = ref(context)

    @property
    def context(self) -> 'FileContext':
        rv = self._context()
        if rv is None:
            raise RuntimeError('context went away, program is invalid')
        return rv

    @abstractmethod
    def get_desired_filename(self):
        """
        return desired filename
        """
        raise NotImplementedError()

    @abstractmethod
    def prepare(self):
        """
        update file context meta & config
        """
        raise NotImplementedError()

    @abstractmethod
    def render_contents(self) -> str:
        """
        return file content
        """
        raise NotImplementedError()

    @abstractmethod
    def run(self):
        """
        render desired file
        """
        raise NotImplementedError()


class CopyParser(BaseParser):
    """A program that copies a file over unchanged"""

    def prepare(self):
        return

    def render_contents(self):
        return ''

    def run(self):
        self.context.make_destination_folder()
        shutil.copy(self.context.full_source_filename,
                    self.context.full_destination_filename)

    def get_desired_filename(self):
        return self.context.source_filename


class TemplateParser(BaseParser):

    default_template = 'blog/post.html'

    def __init__(self, context: 'FileContext'):
        super().__init__(context)
        self._parsed = None

    @abstractmethod
    def _parse_title_from_content(self, f) -> Optional[str]:
        raise NotImplementedError()

    def prepare(self):
        """ parse file meta """
        headers = []
        with self.context.open_source_file() as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    break
                headers.append(line)
            title = self._parse_title_from_content(f)
        try:
            if headers[0] != '---':
                headers.insert(0, '---')
            if headers[-1] == '---':
                headers.pop()
            cfg = yaml.safe_load(StringIO('\n'.join(headers)))
        except Exception as e:
            raise Exception(f'file meta error, meta={headers}') from e

        if cfg:
            if not isinstance(cfg, dict):
                source_file = self.context.source_filename
                raise ValueError(f'expected dict config in file '
                                 f'"{source_file}", got: {cfg}')

            self.context.config = self.context.config.add_from_dict(cfg)
            self.context.destination_filename = cfg.get(
                'destination_filename',
                self.context.destination_filename)

            title = cfg.get(FILE_META_TITLE) or title
            if title is not None:
                self.context.meta.title = title

            pub_date = cfg.get(FILE_META_PUB_DATE)
            if pub_date is not None:
                if isinstance(pub_date, date):
                    pub_date = datetime(
                        pub_date.year, pub_date.month, pub_date.day)
                if isinstance(pub_date, datetime):
                    self.context.meta.pub_date = pub_date

            type_ = cfg.get(FILE_META_TYPE)
            if type_ is not None:
                self.context.meta.type = type_

            summary = cfg.get(FILE_META_SUMMARY)
            if summary is not None:
                self.context.meta.summary = summary

    def get_desired_filename(self):
        base, _ = os.path.splitext(self.context.source_filename)
        return f'{base}.html'

    def render_contents(self):
        return self.parsed['content']

    @abstractmethod
    def parse(self) -> dict:
        raise NotImplementedError

    @property
    def parsed(self) -> dict:
        if not self._parsed:
            self._parsed = self.parse()
        return self._parsed

    def _get_template_context(self):
        ctx = dict()
        ctx['post'] = self.parsed
        return ctx

    def run(self):
        template_name = (self.context.config.get(FILE_CONFIG_TEMPLATE) or
                         self.default_template)
        context = self._get_template_context()
        rv = self.context.render_template(template_name, context)
        with self.context.open_destination_file() as f:
            f.write(rv + '\n')


class RSTParser(TemplateParser):
    """A program that renders an rst file into a template"""

    _fragment_cache = None

    def _parse_title_from_content(self, f) -> Optional[str]:
        buffer = []
        for line in f:
            line = line.rstrip()
            if not line:
                break
            buffer.append(line)
        return self._render_rst('\n'.join(buffer)).get('title')

    def _render_rst(self, contents: str) -> dict:
        settings = {
            'initial_header_level': self.context.config.get(
                'rst_header_level', 2),
            'blogme_context': self
        }
        parts = publish_parts(source=contents,
                              writer_name='html4css1',
                              settings_overrides=settings)
        return {
            'title': Markup(parts['title']).striptags(),
            'html_title': Markup(parts['html_title']),
            'content': Markup(parts['fragment'])
        }

    def parse(self) -> dict:
        if self._fragment_cache is not None:
            return self._fragment_cache

        with self.context.open_source_file() as f:
            while f.readline().strip():
                pass
            contents = f.read()

        fragments = self._render_rst(contents)
        self._fragment_cache = fragments
        return fragments


class MDParser(TemplateParser):
    """
    A program that renders an markdown file into a template
    """

    def __init__(self, context: 'FileContext'):
        style = context.config.root_get('modules.pygments.style')
        c = CodeHiliteExtension(
            pygments_style=style or 'tango',  guess_lang='True')
        self.md = Markdown(
            output_format='html5',
            safe_mode='escape',
            enable_attributes=True,
            extensions=[
                'meta', 'fenced_code', 'footnotes', 'attr_list',
                'def_list', 'tables', 'abbr', c
            ]
        )
        super().__init__(context)

    def _parse_title_from_content(self, f) -> Optional[str]:
        return

    def parse(self) -> dict:

        self.md.reset()
        with self.context.open_source_file() as f:
            parsed = self.md.convert(f.read())
        post = dict(
            content=Markup(parsed),
        )
        return post


