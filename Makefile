# A self-documenting Makefile
# You can set these variables from the command line, and also
# from the environment for the first two.
SOURCEDIR = ./ocxwiki
PACKAGE := ocxwiki

uv-install:  ## Install all project dependencies using uv
	@uv sync
ui: uv-install
.PHONY: ui

uv-install-dev:  ## Install project and dev dependencies using uv
	@uv sync --extra dev
uid: uv-install-dev
.PHONY: uid

uv-update:  ## Update all dependencies to their latest allowed versions
	@uv lock --upgrade
	@uv sync
uu: uv-update
.PHONY: uu

uv-add:  ## Add a new dependency: make uv-add pkg=<package>
	@uv add $(pkg)
ua: uv-add
.PHONY: ua

uv-remove:  ## Remove a dependency: make uv-remove pkg=<package>
	@uv remove $(pkg)
ur: uv-remove
.PHONY: ur

uv-lock:  ## Regenerate the uv.lock file without installing
	@uv lock
ul: uv-lock
.PHONY: ul

venv:  ## Create a virtual environment using uv
	@uv venv
.PHONY: venv

# Color output
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# DOCUMENTATION ##############################################################
SPHINXBUILD = sphinx-build -E -b html docs dist/docs
COVDIR = "htmlcov"

doc-serve: ## Open the html docs built by Sphinx
	@cmd /c start "dist/docs/index.html"

ds: doc-serve
.PHONY: ds

doc-help:  ## Sphinx options when running make from the docs folder
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

doc: ## Build the html docs using Sphinx. For other Sphinx options, run make in the docs folder
	@$(SPHINXBUILD)  -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@$(SPHINXBUILD)  "$(SOURCEDIR)" "$(BUILDDIR)/$(SPHINXOPTS)" -b "$(SPHINXOPTS)"

# RUN ##################################################################

run: ## Start ocxwiki CLI in batch mode
	@uv run python cli.py
.PHONY: run

interactive: ## Start ocxwiki CLI in interactive mode
	@uv run python cli.py interactive
.PHONY: interactive

# TESTS #######################################################################

FAILURES := .pytest_cache/pytest/v/cache/lastfailed

test:  ## Run unit and integration tests
	@uv run pytest

test-upd:  ## Update the regression tests baseline
	@uv run pytest --force-regen

tu: test-upd
.PHONY: tu

test-cov:  ## Show the test coverage report
	cmd /c start $(CURDIR)/$(COVDIR)/index.html

tc: test-cov
.PHONY: tc

# CHECKS ######################################################################
check-lint:  ## Run ruff linter and formatter with auto-fix
	@printf "\n${BLUE}Running ruff check with auto-fix...${NC}\n"
	@uv run ruff check . --fix
	@printf "${BLUE}\nRunning ruff format...${NC}\n"
	@uv run ruff format .

# BUILD #######################################################################

build:  ## Build the package using uv
	@uv build
.PHONY: build

build-exe:  ## Build a bundled executable using pyinstaller
	@uv run pyinstaller main.spec
.PHONY: build-exe


# HELP ########################################################################

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

#-----------------------------------------------------------------------------------------------





