import sys
from pathlib import Path

sys.path.insert(0, str(Path("..").resolve()))

import snap7  # noqa: E402

# -- General configuration -----------------------------------------------------

extensions = ["sphinx.ext.autodoc", "sphinx.ext.coverage", "sphinx.ext.viewcode", "sphinx.ext.napoleon"]

templates_path = ["_templates"]

source_suffix = ".rst"

master_doc = "index"

project = "python-snap7"
copyright = "2013-2026, Gijs Molenaar, Stephan Preeker"  # noqa: A001

version = snap7.__version__
release = snap7.__version__

exclude_patterns = ["_build"]

pygments_style = "sphinx"


# -- Options for HTML output ---------------------------------------------------

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]

htmlhelp_basename = "python-snap7doc"


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {}

latex_documents = [
    ("index", "python-snap7.tex", "python-snap7 Documentation", "Gijs Molenaar, Stephan Preeker", "manual"),
]


# -- Options for manual page output --------------------------------------------

man_pages = [("index", "python-snap7", "python-snap7 Documentation", ["Gijs Molenaar, Stephan Preeker"], 1)]


# -- Options for Texinfo output ------------------------------------------------

texinfo_documents = [
    (
        "index",
        "python-snap7",
        "python-snap7 Documentation",
        "Gijs Molenaar, Stephan Preeker",
        "python-snap7",
        "Pure Python S7 communication library for Siemens S7 PLCs.",
        "Miscellaneous",
    ),
]


# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None
napoleon_attr_annotations = True
