"""Guard-rail tests for Gridiron Locker.

This file exists so the suite can be discovered as a *package*, which is what
makes the top-level-directory flag work:

    python3 -m unittest discover -s tests -p "test_*.py"          # works either way
    python3 -m unittest discover -s tests -t . -p "test_*.py"     # needs this file
    python3 tests/test_layout.py                                  # works either way

Without it, the second form dies before running a single test:

    ImportError: Start directory is not importable: '<repo>/tests'

unittest resolves the start directory against sys.path to derive a module name;
with ``-t .`` the start directory is a subdirectory of the top level, so it has
to be a real package. README.md documents the second form, which is why this is
here rather than being left as a "just use the first form" footnote.

The modules in this package still insert ``src/`` and ``tests/`` onto
``sys.path`` themselves, so importing them as ``tests.test_x`` or running them
as ``__main__`` both resolve their helpers the same way.
"""
