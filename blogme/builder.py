# -*- coding: utf-8 -*-

import os
from fnmatch import fnmatch
from urllib.parse import urlparse
import datetime

from jinja2 import Environment, FileSystemLoader
from babel import Locale, dates
from werkzeug.routing import Map, Rule
from werkzeug.urls import url_unquote

from blogme.signals import (
    before_file_processed, before_template_rendered,
    before_build_finished, before_file_built,
    after_file_prepared, after_file_published,
    before_build
)
from blogme.modules import find_module
from blogme.file_parser import RSTParser, CopyParser, MDParser, BaseParser
from blogme.config import Config


builtin_file_parsers = {
    'md': MDParser,
    'rst': RSTParser,
    'copy': CopyParser
}
default_output_folder = '_build'
builtin_templates = os.path.join(os.path.dirname(__file__), 'templates')
builtin_static = os.path.join(os.path.dirname(__file__), 'static')


class FileMeta:

    def __init__(self):
        self.title: str = 'UNKNOWN'
        self.pub_date: datetime.date = None
        self.summary: str = None
        self.type: str = 'post'


class FileContext:
    """
    public attr
        - config
        - meta
        - slug
        - content
        - source_filename
        - full_source_filename
        - destination_filename
        - full_destination_filename
        - is_new
        - needs_build
        - public


    public method
        - open_source_file             // for reading source file
        - make_destination_folder      // for witing/copy dest file
        - open_destination_file        // for writing dest file
        - run                          // build
    """
    default_file_parsers = {
        '*.rst': 'rst',
        '*.md': 'md'
    }

    def __init__(self, builder: 'Builder', config: Config,
                 source_filename: str, prepare: bool = False):
        self.builder = builder
        self.config = config
        # file meta
        self.meta = FileMeta()
        # relative (to the project folder) source filename
        self.source_filename = source_filename
        # processed html link tags
        self._link_tags = []
        # find the right text parser

        self._file_parser = self._guess_file_parser(source_filename)
        # relative (to the output folder) destination filename
        self.destination_filename = self._file_parser.get_desired_filename()
        # parse meta info
        if prepare:
            self._file_parser.prepare()
            after_file_prepared.send(self)
            if self.public:
                after_file_published.send(self)

    def _guess_file_parser(self, filename: str) -> BaseParser:
        file_parser_name = self.config.get('file_parser')
        if not file_parser_name:

            mapping = (self.config.list_entries('file_parsers') or
                       self.default_file_parsers)
            for pattern, text_parser_name in mapping.items():
                if fnmatch(filename, pattern):
                    file_parser_name = text_parser_name
                    break
            else:
                file_parser_name = 'copy'
        return builtin_file_parsers[file_parser_name](self)

    @property
    def is_new(self):
        return not os.path.exists(self.full_destination_filename)

    @property
    def public(self):
        return self.config.get('public', True)

    @property
    def slug(self):
        return self._file_parser.get_desired_filename().replace('\\', '/')

    @property
    def content(self):
        return self._file_parser.render_contents()

    @property
    def full_destination_filename(self):
        return os.path.join(self.builder.project_folder,
                            (self.config.get('output_folder') or
                             default_output_folder),
                            self.destination_filename)

    @property
    def full_source_filename(self):
        return os.path.join(self.builder.project_folder, self.source_filename)

    @property
    def needs_build(self):
        if self.is_new:
            return True
        src = self.full_source_filename
        dst = self.full_destination_filename
        return os.path.getmtime(dst) < os.path.getmtime(src)

    def make_destination_folder(self):
        folder = os.path.dirname(self.full_destination_filename)
        if not os.path.isdir(folder):
            os.makedirs(folder)

    def open_source_file(self, mode='r'):
        return open(self.full_source_filename, mode)

    def open_destination_file(self, mode='w'):
        self.make_destination_folder()
        return open(self.full_destination_filename, mode)

    def _get_default_template_context(self):
        return {
            'source_filename':  self.source_filename,
            'links':            self._link_tags,
            'ctx':              self,
            'config':           self.config
        }

    def render_template(self, template_name, context=None):
        real_context = self._get_default_template_context()
        if context:
            real_context.update(context)
        return self.builder.render_template(template_name, real_context)

    # def render_summary(self):
    #     return self.meta.summary or ''

    def add_stylesheet(self, href, type=None, media=None):
        if type is None:
            type = 'text/css'
        self._link_tags.append({
            'href':     self.builder.link_to('static', filename=href),
            'type':     type,
            'media':    media,
            'rel':      'stylesheet'
        })

    def run(self, force_build: bool = False):
        before_file_processed.send(self)
        if force_build or self.needs_build:
            self._build()

    def _build(self):
        before_file_built.send(self)
        self._file_parser.run()


class BuildError(ValueError):
    pass


class RouteAndTemplateMixin:
    """
    public attr
        - prefix_path
    public method
        - register_url
        - link_to
        - open_link_file
        - update_jinja_env
        - render_template
    """
    default_template_path = '_templates'

    def __init__(self):
        self._locale = Locale(self.config.root_get('locale') or 'zh')
        self._url_map = Map()
        parsed = urlparse(self.config.root_get('canonical_url'))
        self.prefix_path = parsed.path
        self._url_adapter = self._url_map.bind(
            'dummy.invalid', script_name=self.prefix_path)
        self.register_url('home', '/')
        self.register_url('post', '/<path:slug>')

        template_path = os.path.join(
            self.project_folder,
            self.config.root_get('template_path') or self.default_template_path
        )

        self._jinja_env = Environment(
            loader=FileSystemLoader([template_path, builtin_templates]),
            autoescape=self.config.root_get('template_autoescape', True),
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'],
        )
        self._jinja_env.globals.update(
            link_to=self.link_to,
            format_datetime=self._format_datetime,
            format_date=self._format_date,
            format_time=self._format_time,
            config=self.config
        )

    def update_jinja_env(self, **kwargs):
        self._jinja_env.globals.update(kwargs)

    def render_template(self, template_name, context=None):
        if context is None:
            context = {}
        context['builder'] = self
        context.setdefault('config', self.config)
        tmpl = self._jinja_env.get_template(template_name)
        before_template_rendered.send(tmpl, context=context)
        return tmpl.render(context)

    def register_url(self, key, rule=None, config_key=None,
                     config_default=None, **extra):
        if config_key is not None:
            rule = self.config.root_get(config_key, config_default)
        self._url_map.add(Rule(rule, endpoint=key, **extra))

    def link_to(self, _key, **values):
        return self._url_adapter.build(_key, values)

    def _get_link_filename(self, _key, **values):
        link = url_unquote(self.link_to(_key, **values)[len(self.prefix_path) + 1:])
        if not link or link.endswith('/'):
            link += 'index.html'
        return os.path.join(self.dest_folder, link)

    def open_link_file(self, _key, mode='w', **values):
        filename = self._get_link_filename(_key, **values)
        folder = os.path.dirname(filename)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        return open(filename, mode)

    def _format_datetime(self, datetime=None, format='medium'):
        return dates.format_datetime(datetime, format, locale=self._locale)

    def _format_time(self, time=None, format='medium'):
        return dates.format_time(time, format, locale=self._locale)

    def _format_date(self, date=None, format='medium', locale=None):

        return dates.format_date(
            date, format, locale=Locale(locale) if locale else self._locale)


class Builder(RouteAndTemplateMixin):
    """
    public attr:
        - project_folder (full)
        - config
        - dest_folder (full)
        - static_folder (full)
    public method:
        - get_storage                 // for module share data
        - anything_needs_build
        - run                         // build
        - debug_serve                 // run a dev server
    """
    default_ignores = ('.*', '_*', 'config.yml', 'Makefile', 'README.*', '*.conf', )
    default_static_folder = 'static'

    def __init__(self, project_folder, config):
        self.config = config
        self.project_folder = os.path.abspath(project_folder)
        RouteAndTemplateMixin.__init__(self)
        static = self.config.root_get('static_folder') or self.default_static_folder
        self.register_url('static', f'/{static}/<path:filename>')
        # setup module
        self._modules = []
        self._storage = {}
        self._setup_module()

    def _setup_module(self):
        for module in self.config.root_get('active_modules') or []:
            mod = find_module(module)
            if mod:
                mod.setup(self)
                self._modules.append(mod)
                print(f'activate module of {module}')

    @property
    def dest_folder(self):
        return os.path.join(
            self.project_folder,
            self.config.root_get('output_folder') or default_output_folder
        )

    @property
    def static_folder(self):
        return os.path.join(
            self.dest_folder,
            self.config.root_get('static_folder') or self.default_static_folder
        )

    def get_storage(self, module):
        return self._storage.setdefault(module, {})

    def _filter_files(self, files, config):
        patterns = config.merged_get('ignore_files')
        if patterns is None:
            patterns = self.default_ignores

        result = []
        for filename in files:
            for pattern in patterns:
                if fnmatch(filename, pattern):
                    break
            else:
                result.append(filename)
        return result

    def _iter_contexts(self, prepare=True):
        last_config = self.config
        cutoff = len(self.project_folder) + 1
        for dirpath, dirnames, filenames in os.walk(self.project_folder):
            local_config = last_config
            local_config_filename = os.path.join(dirpath, 'config.yml')
            if os.path.isfile(local_config_filename):
                local_config = last_config.add_from_file(local_config_filename)

            dirnames[:] = self._filter_files(dirnames, local_config)
            filenames = self._filter_files(filenames, local_config)

            for filename in filenames:
                yield FileContext(self, local_config, os.path.join(
                    dirpath[cutoff:], filename), prepare)

    def anything_needs_build(self):
        for context in self._iter_contexts(prepare=False):
            if context.needs_build:
                return True
        return False

    def run(self, force_build: bool = False):

        self._storage.clear()
        before_build.send(self)
        contexts = list(self._iter_contexts())

        for context in contexts:
            key = context.is_new and 'A' or 'U'
            context.run(force_build)
            print(key, context.source_filename)

        before_build_finished.send(self)

    def debug_serve(self, host='0.0.0.0', port=5200):
        from blogme.server import Server
        print('Serving on http://{}:{}{}'.format(host, port, self.prefix_path))
        try:
            Server(host, port, self).serve_forever()
        except KeyboardInterrupt:
            pass
