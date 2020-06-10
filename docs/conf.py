#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# CodeGrade documentation build configuration file, created by
# sphinx-quickstart on Thu Jun 29 15:43:19 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys
import subprocess
from datetime import date

import sphinx_fontawesome

from sphinx.search import IndexBuilder

sys.path.insert(0, os.path.abspath('../'))
sys.path.append(os.path.abspath("./_ext"))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.doctest',
    'sphinx.ext.githubpages',
    'sphinxcontrib.httpdomain',
    'sphinxcontrib.autohttp.flask',
    'sphinxcontrib.autohttp.flaskqref',
    'sphinx_autodoc_typehints',
    'sphinx_fontawesome',
    'example',
]

# Don't show internal routes in the documenation
http_index_ignore_prefixes = ['/api/v-internal']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'CodeGrade'
copyright = str(date.today().year) + ', CodeGrade'
author = 'CodeGrade Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = subprocess.check_output(['git', 'describe', '--abbrev=0',
                                   '--tags', 'stable']).decode('utf-8').strip()
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'CodeGradedoc'

# -- Options for LaTeX output ---------------------------------------------

latex_engine = 'xelatex'
latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
    'inputenc': '',
    'utf8extra': '',
    'preamble':
        r'''
\setcounter{tocdepth}{2}
\usepackage{comment}
\excludecomment{sphinxtheindex}
\let\endsphinxtheindex\relax
''',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'CodeGrade.tex', 'CodeGrade User Manual', author, 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, 'codegrade', 'CodeGrade Manual', [author], 1)]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc, 'CodeGrade', 'CodeGrade User Manual', author, 'CodeGrade',
        'Codegrade is a blended learning tool that makes grading programming '
        + 'assignments more intuitive.', 'Miscellaneous'
    ),
]

todo_include_todos = True

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'https://docs.python.org/3': None,
    'http://werkzeug.pocoo.org/docs/latest/': None,
    'http://flask.pocoo.org/docs/latest/': None,
    'http://sqlalchemy-utils.readthedocs.io/en/latest': None,
}

html_favicon = '../static/favicon/favicon.ico'
html_logo = '_static/_images/logo.svg'
html_theme_options = {
    'logo_only': True,
}

existing_feed = IndexBuilder.feed


def new_feed(self, docname, filename, *args, **kwargs):
    if filename in {
        'running.rst',
        'api.rst',
        'building.rst',
        'code.rst',
        'developerdocs.rst',
        'psef_api/psef.rst',
    }:
        return
    return existing_feed(self, docname, filename, *args, **kwargs)


IndexBuilder.feed = new_feed
