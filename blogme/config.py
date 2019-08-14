# -*- coding: utf-8 -*-

from typing import Any, Union, Optional, List

import yaml


missing = object()


class Config:
    """
    A stacked config
    """

    def __init__(self):
        self.stack: List[dict] = []

    def __getitem__(self, key: str) -> Any:
        for layer in reversed(self.stack):
            rv = layer.get(key, missing)
            if rv is not missing:
                return rv
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def list_entries(self, key) -> dict:
        rv = {}
        prefix = key + '.'
        for layer in self.stack:
            for key, value in layer.items():
                if key.startswith(prefix):
                    rv[key] = value
        return rv

    def merged_get(self, key: str) -> Union[dict, list]:
        result = None
        for layer in self.stack:
            rv = layer.get(key, missing)
            if rv is not missing:
                if result is None:
                    result = rv
                else:
                    if isinstance(result, list):
                        result.extend(rv)
                    elif isinstance(result, dict):
                        result.update(rv)
                    else:
                        raise ValueError('expected list or dict')
        return result

    def root_get(self, key: str, default: Any = None) -> Any:
        if not self.stack:
            return None
        return self.stack[0].get(key, default)

    def add_from_dict(self, cfg: dict) -> 'Config':
        """
        Returns a new config from this config with another layer added
        from a given dictionary.
        """
        layer = {}
        rv = Config()
        rv.stack = self.stack + [layer]

        def _walk(d, prefix):
            for key, value in d.items():
                if isinstance(value, dict):
                    _walk(value, prefix + key + '.')
                else:
                    layer[prefix + key] = value
        _walk(cfg, '')
        return rv

    def add_from_file(self, filename: str) -> Optional['Config']:
        """
        Returns a new config from this config with another layer added
        from a given config file.
        """
        with open(filename) as f:
            d = yaml.safe_load(f)
            if not d:
                return
            if not isinstance(d, dict):
                raise ValueError('Configuration has to contain a dict')
            return self.add_from_dict(d)

    def pop(self) -> None:
        self.stack.pop()
