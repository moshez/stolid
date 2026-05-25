import functools
import os
import re
import urllib.request

import nox

nox.options.envdir = "build/nox"
nox.options.sessions = ["lint", "tests", "mypy", "docs", "dry_release"]

VERSIONS = ["3.12", "3.13", "3.14"]

PUBLISH_ACTION = "pypa/gh-action-pypi-publish"


def _publish_twine_requirement():
    """The twine pin the release workflow uploads with.

    Read the version straight from the action pinned in release.yml instead
    of hardcoding it, so the dry run always validates with the same twine
    that performs the real upload. A separate pin could silently fall behind
    and let a release pass here only to be rejected on upload.
    """
    workflow = os.path.join(
        os.path.dirname(__file__), ".github", "workflows", "release.yml"
    )
    with open(workflow, encoding="utf-8") as stream:
        sha = re.search(rf"{PUBLISH_ACTION}@([0-9a-f]{{40}})", stream.read())
    url = (
        f"https://raw.githubusercontent.com/{PUBLISH_ACTION}/{sha.group(1)}"
        "/requirements/runtime.txt"
    )
    with urllib.request.urlopen(url) as response:
        runtime = response.read().decode()
    return re.search(r"^twine==\S+", runtime, re.MULTILINE).group(0)


@nox.session(python=VERSIONS)
def tests(session):
    tmpdir = session.create_tmp()
    session.install("-r", "requirements-tests.txt")
    session.install("-e", ".")
    tests = session.posargs or ["stolid.tests"]
    session.run(
        "coverage",
        "run",
        "--branch",
        "--source=stolid",
        "--omit=**/__main__.py",
        "-m",
        "virtue",
        *tests,
        env=dict(COVERAGE_FILE=os.path.join(tmpdir, "coverage"), TMPDIR=tmpdir),
    )
    fail_under = "--fail-under=100"
    session.run(
        "coverage",
        "report",
        fail_under,
        "--show-missing",
        "--skip-covered",
        env=dict(COVERAGE_FILE=os.path.join(tmpdir, "coverage")),
    )


@nox.session(python=VERSIONS[-1])
def build(session):
    session.install("build")
    session.run("python", "-m", "build", "--wheel")


@nox.session(python=VERSIONS[-1])
def dry_release(session):
    """Build sdist and wheel and validate them with twine (does not upload)."""
    output = os.path.abspath(os.path.join(session.create_tmp(), "dist"))
    session.install("build", _publish_twine_requirement())
    session.run("python", "-m", "build", "--outdir", output)
    files = sorted(os.path.join(output, name) for name in os.listdir(output))
    session.run("twine", "check", "--strict", *files)


@nox.session(python=VERSIONS[-1])
def lint(session):
    files = ["src/", "noxfile.py"]
    session.install("-r", "requirements-lint.txt")
    session.install("-e", ".")
    session.run("black", "--check", "--diff", *files)
    session.run("python", "-m", "stolid", "src/")


@nox.session(python=VERSIONS[-1])
def mypy(session):
    session.install("-r", "requirements-mypy.txt")
    session.install("-r", "requirements-tests.txt")
    session.install("-e", ".")
    session.run(
        "mypy",
        "--strict",
        "--disallow-any-explicit",
        "src/",
    )


@nox.session(python=VERSIONS[-1])
def docs(session):
    """Build the documentation."""
    output_dir = os.path.abspath(os.path.join(session.create_tmp(), "output"))
    doctrees, html = map(
        functools.partial(os.path.join, output_dir), ["doctrees", "html"]
    )
    session.run("rm", "-rf", output_dir, external=True)
    session.install("-r", "requirements-docs.txt")
    session.install("-e", ".")
    sphinx = ["sphinx-build", "-b", "html", "-W", "-d", doctrees, ".", html]
    session.cd("doc")
    session.run(*sphinx)


@nox.session(python=VERSIONS[-1])
def refresh_deps(session):
    """Refresh the requirements-*.txt files"""
    session.install("pip-tools")
    for deps in ["tests", "docs", "lint", "mypy"]:
        session.run(
            "pip-compile",
            "--extra",
            deps,
            "pyproject.toml",
            "--output-file",
            f"requirements-{deps}.txt",
        )
