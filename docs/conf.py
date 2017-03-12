#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# asynctnt documentation build configuration file, created by
# sphinx-quickstart on Sun Mar 12 18:57:44 2017.
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

import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath('..'))


def find_version():
    import re
    for line in open("../asynctnt/__init__.py"):
        if line.startswith("__version__"):
            return re.match(
                r"""__version__\s*=\s*(['"])([^'"]+)\1""", line).group(2)

_ver = find_version()


# -- General configuration ------------------------------------------------

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.viewcode',
              'sphinxcontrib.asyncio']

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = 'asynctnt'
copyright = '2017, igorcoding'
author = 'igorcoding'

version = _ver
release = _ver

language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_static_path = ['_static']


# -- Options for HTMLHelp output ------------------------------------------
htmlhelp_basename = 'asynctntdoc'


# -- Options for LaTeX output ---------------------------------------------

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
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'asynctnt.tex', 'asynctnt Documentation',
     'igorcoding', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'asynctnt', 'asynctnt Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'asynctnt', 'asynctnt Documentation',
     author, 'asynctnt', 'One line description of project.',
     'Miscellaneous'),
]



