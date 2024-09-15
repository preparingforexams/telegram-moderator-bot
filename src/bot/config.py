import logging
from pathlib import Path

import yaml

_LOG = logging.getLogger(__name__)


def load_config_dict_from_yaml(config_file: Path) -> dict | None:
    if not config_file.is_file():
        _LOG.warning("No config found")
        return None

    with open(config_file, "r", encoding="utf-8") as f:
        config_dict = yaml.load(f, yaml.Loader)
        if not config_dict:
            _LOG.warning("Config is empty")
            return None

    return config_dict