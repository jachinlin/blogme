# -*- coding: utf-8 -*-

from jinja2 import contextfunction, Markup

from blogme.signals import before_file_processed
from blogme.builder import Builder, FileContext


html = """<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/8.7.0/mermaid.min.js" integrity="sha512-AO6jCf8hcA8fZ2mL0Ij911i4bP0Cm93/DcjvlD7obOOmZuXsqzEoIsToU+gADi7rczmmQzwuR6nCfbBAZgQK6Q==" crossorigin="anonymous"></script>
<script>mermaid.initialize({startOnLoad:true});</script>
"""


def inject_stylesheet(context: FileContext, **kwargs):
    context.add_stylesheet('mermaid.css')


@contextfunction
def init_mermaid(context):
    return Markup(html)


def setup(builder: Builder):
    before_file_processed.connect(inject_stylesheet)
    builder.update_jinja_env(init_mermaid=init_mermaid)
