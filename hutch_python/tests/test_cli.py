import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import IPython.core.completer
import pytest
from conftest import cli_args, restore_logging

import hutch_python.cli
from hutch_python.cli import HutchPythonArgs, main
from hutch_python.load_conf import load

from .conftest import skip_if_win32_generic

logger = logging.getLogger(__name__)

CFG_PATH = Path(os.path.dirname(__file__)) / 'conf.yaml'
CFG = str(CFG_PATH)


@pytest.fixture(scope='function')
def no_ipython_launch(monkeypatch):
    def no_op(*args, **kwargs):
        pass
    monkeypatch.setattr(hutch_python.cli, 'start_ipython', no_op)


@skip_if_win32_generic
def test_main_normal(no_ipython_launch):
    logger.debug('test_main_normal')

    with cli_args(['hutch_python', '--cfg', CFG]):
        with restore_logging():
            main()


@skip_if_win32_generic
def test_main_no_args(no_ipython_launch):
    logger.debug('test_main_no_args')

    with cli_args(['hutch_python']):
        with restore_logging():
            main()


@skip_if_win32_generic
def test_debug_arg(no_ipython_launch):
    logger.debug('test_debug_arg')

    with cli_args(['hutch_python', '--cfg', CFG, '--debug']):
        with restore_logging():
            main()


@skip_if_win32_generic
def test_sim_arg(no_ipython_launch):
    logger.debug('test_sim_arg')

    with cli_args(['hutch_python', '--cfg', CFG, '--sim']):
        with restore_logging():
            main()


def test_create_arg():
    logger.debug('test_create_arg_dev')
    hutch = 'temp_create'
    test_dir = CFG_PATH.parent.parent.parent / hutch
    if test_dir.exists():
        shutil.rmtree(test_dir)

    with cli_args(['hutch_python', '--create', hutch]):
        with restore_logging():
            main()

    assert test_dir.exists()

    # Make sure conf.yml is valid
    load(str(test_dir / 'conf.yml'))
    shutil.rmtree(test_dir)


def run_hpy_and_exit(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "hutch_python"] + list(args),
        input="exit\n",
        universal_newlines=True,
        capture_output=True,
    )


@pytest.mark.timeout(30)
def test_hist_file_arg():
    logger.debug("test_hist_file_arg")
    test_hist_file = (CFG_PATH.parent / "history.sqlite").resolve()
    bad_hist_file = (CFG_PATH.parent / "aesefiudh" / "history.sqlite").resolve()
    memory_hist_file = ":memory:"

    # Test that the sqlite file gets made
    # First, need to remove the file if it already exists
    if test_hist_file.exists():
        test_hist_file.unlink()

    # Run with the good arg and exit
    run_hpy_and_exit("--hist-file", str(test_hist_file))
    # Was the history file created?
    assert test_hist_file.exists()
    # Remove the file for future tests
    test_hist_file.unlink()
    # With the bad hist file we should still run ok with just a warning
    run_hpy_and_exit("--hist-file", str(bad_hist_file))
    assert not test_hist_file.exists()
    # Same with the in-memory choice
    run_hpy_and_exit("--hist-file", memory_hist_file)
    assert not test_hist_file.exists()


@skip_if_win32_generic
def test_run_script():
    logger.debug('test_run_script')

    # Will throw a name error unless we run the script inside the full env
    with cli_args(['hutch_python', '--cfg', CFG, '--debug',
                   str(Path(__file__).parent / 'script.py')]):
        with restore_logging():
            main()


def test_ipython_tab_completion():
    class MyTest:
        THIS_SHOULD_NOT_BE_THERE = None

        def __dir__(self):
            return ['foobar']

    ns = {'a': MyTest()}

    # Side-effect of the following is monkey-patching `dir2` to "fix" this for
    # us.
    hutch_python.cli.configure_ipython_session(HutchPythonArgs())

    completer = IPython.core.completer.Completer(namespace=ns)
    completer.limit_to__all__ = False
    assert 'a.THIS_SHOULD_NOT_BE_THERE' not in completer.attr_matches('a.')
    assert completer.attr_matches('a.') == ['a.foobar']
