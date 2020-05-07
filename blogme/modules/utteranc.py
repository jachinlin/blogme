# -*- coding: utf-8 -*-

from jinja2 import contextfunction, Markup


html = """<script src="https://utteranc.es/client.js"
    repo="{repo}"
    issue-term="{issue_term}"
    theme="{theme}"
    crossorigin="anonymous"
    async>
</script>
"""


@contextfunction
def get_utteranc(context):
    repo = context['builder'].config.root_get('modules.utteranc.repo')
    issue_term = context['builder'].config.root_get('modules.utteranc.issue_term', 'title')
    theme = context['builder'].config.root_get('modules.utteranc.theme', 'github-light')

    return Markup(html.format(repo=repo, issue_term=issue_term, theme=theme))


def setup(builder):
    builder.update_jinja_env(get_utteranc=get_utteranc)
