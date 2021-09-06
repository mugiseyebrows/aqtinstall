import re
import sys

import pytest

from aqt.exceptions import CliInputError
from aqt.installer import Cli
from aqt.metadata import Version


@pytest.fixture()
def expected_help():
    return (
        "usage: aqt [-h] [-c CONFIG]\n"
        "           {install-qt,install-tool,install-doc,install-example,install-src,list-qt,list-tool,"
        "install,tool,doc,example,src,help,version}\n"
        "           ...\n"
        "\n"
        "Another unofficial Qt Installer.\n"
        "aqt helps you install Qt SDK, tools, examples and others\n"
        "\n"
        "optional arguments:\n"
        "  -h, --help            show this help message and exit\n"
        "  -c CONFIG, --config CONFIG\n"
        "                        Configuration ini file.\n"
        "\n"
        "subcommands:\n"
        "  aqt accepts several subcommands:\n"
        "  install-* subcommands are commands that install components\n"
        "  list-* subcommands are commands that show available components\n"
        "  \n"
        "  commands {install|tool|src|examples|doc} are deprecated and marked for removal\n"
        "\n"
        "  {install-qt,install-tool,install-doc,install-example,install-src,list-qt,list-tool,"
        "install,tool,doc,example,src,help,version}\n"
        "                        Please refer to each help message by using '--help' with each subcommand\n"
    )


def test_cli_help(capsys, expected_help):
    cli = Cli()
    cli.run(["help"])
    out, err = capsys.readouterr()
    assert out == expected_help


def test_cli_check_module():
    cli = Cli()
    cli._setup_settings()
    assert cli._check_modules_arg("5.11.3", ["qtcharts", "qtwebengine"])
    assert not cli._check_modules_arg("5.7", ["not_exist"])
    assert cli._check_modules_arg("5.14.0", None)
    assert not cli._check_modules_arg("5.15.0", ["Unknown"])


def test_cli_check_combination():
    cli = Cli()
    cli._setup_settings()
    assert cli._check_qt_arg_combination("5.11.3", "linux", "desktop", "gcc_64")
    assert cli._check_qt_arg_combination("5.11.3", "mac", "desktop", "clang_64")
    assert not cli._check_qt_arg_combination("5.14.0", "android", "desktop", "clang_64")


def test_cli_check_version():
    cli = Cli()
    cli._setup_settings()
    assert cli._check_qt_arg_versions("5.12.0")
    assert not cli._check_qt_arg_versions("5.12")


@pytest.mark.parametrize(
    "invalid_version",
    ("5.15", "five-dot-fifteen", "5", "5.5.5.5"),
)
def test_cli_invalid_version(capsys, invalid_version):
    """Checks that invalid version strings are handled properly"""

    # Ensure that invalid_version cannot be a semantic_version.Version
    with pytest.raises(ValueError):
        Version(invalid_version)

    cli = Cli()
    cli._setup_settings()

    matcher = re.compile(
        r"^aqtinstall\(aqt\) v.* on Python 3.*\n"
        r".*Invalid version: '" + invalid_version + r"'! Please use the form '5\.X\.Y'\.\n.*"
    )

    for cmd in (
        ("install-qt", "mac", "desktop", invalid_version),
        ("install-doc", "mac", "desktop", invalid_version),
        ("list-qt", "mac", "desktop", "--modules", invalid_version),
    ):
        cli = Cli()
        assert cli.run(cmd) == 1
        out, err = capsys.readouterr()
        sys.stdout.write(out)
        sys.stderr.write(err)
        assert matcher.match(err)


def test_cli_check_mirror():
    cli = Cli()
    cli._setup_settings()
    assert cli._check_mirror(None)
    arg = ["install-qt", "linux", "desktop", "5.11.3", "-b", "https://download.qt.io/"]
    args = cli.parser.parse_args(arg)
    assert args.base == "https://download.qt.io/"
    assert cli._check_mirror(args.base)


@pytest.mark.parametrize(
    "arch, host, target, version, expect",
    (
        (None, "windows", "desktop", "6.2.0", None),
        ("", "windows", "desktop", "6.2.0", None),
        (None, "linux", "desktop", "6.2.0", "gcc_64"),
        (None, "mac", "desktop", "6.2.0", "clang_64"),
        (None, "mac", "ios", "6.2.0", "ios"),
        (None, "mac", "android", "6.2.0", "android"),
        (None, "mac", "android", "5.12.0", None),
    ),
)
def test_set_arch(arch, host, target, version, expect):
    cli = Cli()
    cli._setup_settings()

    if not expect:
        with pytest.raises(CliInputError) as e:
            cli._set_arch([], arch, host, target, version)
        assert e.type == CliInputError
        assert format(e.value) == "Please supply a target architecture."
        assert e.value.should_show_help is True
    else:
        assert cli._set_arch([], arch, host, target, version) == expect


@pytest.mark.parametrize(
    "cmd, expect_msg, should_show_help",
    (
        (
            "install-qt mac ios 6.2.0 --base not_a_url",
            "The `--base` option requires a url where the path `online/qtsdkrepository` exists.",
            True,
        ),
        (
            "install-qt mac ios 6.2.0 --noarchives",
            "When `--noarchives` is set, the `--modules` option is mandatory.",
            False,
        ),
        (
            "install-qt mac ios 6.2.0 --noarchives --archives",
            "When `--noarchives` is set, the `--modules` option is mandatory.",
            False,
        ),
        (
            "install-qt mac ios 6.2.0 --noarchives --archives --modules qtcharts",
            "Options `--archives` and `--noarchives` are mutually exclusive.",
            False,
        ),
        (
            "install-src mac ios 6.2.0 --kde",
            "KDE patch: unsupported version!!",
            False,
        ),
    ),
)
def test_cli_input_errors(capsys, expected_help, cmd, expect_msg, should_show_help):
    cli = Cli()
    cli._setup_settings()
    assert 1 == cli.run(cmd.split())
    out, err = capsys.readouterr()
    assert out == (expected_help if should_show_help else "")
    assert err.rstrip().endswith(expect_msg)


def test_cli_unexpected_error(monkeypatch, capsys):
    def _mocked_run(*args):
        raise RuntimeError("Some unexpected error")

    monkeypatch.setattr("aqt.installer.Cli.run_install_qt", _mocked_run)

    cli = Cli()
    cli._setup_settings()
    assert 1 == cli.run(["install-qt", "mac", "ios", "6.2.0"])
    out, err = capsys.readouterr()
    assert err.startswith("Some unexpected error")
    assert err.rstrip().endswith(
        "===========================PLEASE FILE A BUG REPORT===========================\n"
        "You have discovered a bug in aqt.\n"
        "Please file a bug report at https://github.com/miurahr/aqtinstall/issues.\n"
        "Please remember to include a copy of this program's output in your report."
    )
