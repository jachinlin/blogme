# -*- coding: utf-8 -*-

import sys
import os
from blogme.config import Config
from blogme.builder import Builder


def get_builder(project_folder: str) -> Builder:
    """
    Runs the builder for the given project folder.
    """
    config_filename = os.path.join(project_folder, 'config.yml')
    config = Config()
    if not os.path.isfile(config_filename):
        raise ValueError('root config file "%s" is required' % config_filename)
    config = config.add_from_file(config_filename)
    return Builder(project_folder, config)


def main():
    """
    Entrypoint for the console script.
    """
    if len(sys.argv) not in (1, 2, 3):
        print('usage: blogme <action> <folder>')
    if len(sys.argv) >= 2:
        action = sys.argv[1]
    else:
        action = 'build'
    if len(sys.argv) >= 3:
        folder = sys.argv[2]
    else:
        folder = os.getcwd()
    if action not in ('build', 'serve', 'rebuild'):
        print('unknown action', action)
    builder = get_builder(folder)

    if action == 'build':
        builder.run()
    elif action == 'rebuild':
        builder.run(force_build=True)
    else:
        builder.debug_serve()
