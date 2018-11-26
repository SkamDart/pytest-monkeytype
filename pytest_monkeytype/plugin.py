# Copyright 2017 Kensho Technologies, Inc.
"""The pytest plugin that calls out to PyAnnotate."""

import os
import sys

if False:
    from typing import Optional
    from monkeytype.tracing import CallTracer

class PyAnnotatePlugin(object):
    """A pytest plugin that profiles function calls to extract type info."""

    def __init__(self, output_file):
        """Create a new PyAnnotatePlugin that analyzes function calls to extract type info."""
        from monkeytype.config import DefaultConfig

        self.config = DefaultConfig()
        self.trace_logger = self.config.trace_logger()
        os.environ[DefaultConfig.DB_PATH_VAR] = output_file
        self.tracer = None  # type: Optional[CallTracer]

    def pytest_collection_finish(self, session):
        """Handle the pytest collection finish hook: configure pyannotate.

        Explicitly delay importing `collect_types` until all tests have been collected. This
        gives gevent a chance to monkey patch the world before importing pyannotate.
        """
        from monkeytype.tracing import CallTracer

        self.tracer = CallTracer(
            logger=self.trace_logger,
            code_filter=self.config.code_filter(),
            sample_rate=None,
        )
        sys.setprofile(self.tracer)

    def pytest_unconfigure(self, config):
        """Unconfigure the pytest plugin. Happens when pytest is about to exit."""
        sys.setprofile(None)
        self.trace_logger.flush()

    def pytest_runtest_call(self):
        """Handle the pytest hook event that a test is about to be run: start type collection."""
        sys.setprofile(self.tracer)

    def pytest_runtest_teardown(self):
        """Handle the pytest test end hook event: stop type collection."""
        sys.setprofile(None)
        self.trace_logger.flush()


def pytest_addoption(parser):
    """Add our --analyze option to the pytest option parser."""
    parser.addoption(
        '--monkeytype-output',
        help='Output file where PyAnnotate stats should be saved.  Eg: "monkeytype.sqlite3"')


def pytest_configure(config):
    """Configure the plugin based on the supplied value for the  option."""
    option_value = config.getoption('--monkeytype-output')
    if option_value:
        base_path = os.path.abspath(option_value)
        config.pluginmanager.register(PyAnnotatePlugin(base_path))
