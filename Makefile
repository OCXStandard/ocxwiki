# A self-documenting Makefile
# You can set these variables from the command line, and also
# from the environment for the first two.
SOURCEDIR = ./ocxwiki
CONDA_ENV = ocxwiki
PACKAGE := ocxwiki

conda-create:  ## Create a new conda environment with the python version and basic development tools
	@conda env create -f environment.yml
	@conda activate $(CONDA_ENV)
cc: conda-create
.PHONY: cc
conda-upd:  ## Update the conda development environment when environment.yml has changed
	@conda env update -f environment.yml
.PHONY:conda-update

conda-activate: ## Activate the conda environment for the project
	@conda activate $(CONDA_ENV)
ca: conda-activate
.PHONY: ca

conda-clean: ## Purge all conda tarballs, log files and caches
	conda clean -a -y
.Phony: conda-clean


# PROJECT DEPENDENCIES ########################################################

# VIRTUAL_ENV ?= ${VENV}
# DEPENDENCIES := $(VIRTUAL_ENV)/$(shell cksum pyproject.toml)


# Color output
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# DOCUMENTATION ##############################################################
SPHINXBUILD = sphinx-build -E -b html docs dist/docs
COVDIR = "htmlcov"

doc-serve: ## Open the the html docs built by Sphinx
	@cmd /c start "dist/docs/index.html"

ds: doc-serve
.PHONY: ds

doc-help:  ## Sphinx options when running make from the docs folder
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

doc: ## Build the html docs using Sphinx. For other Sphinx options, run make in the docs folder
	@$(SPHINXBUILD)  -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@$(SPHINXBUILD)  "$(SOURCEDIR)" "$(BUILDDIR)/$(SPHINXOPTS)" -b "$(SPHINXOPTS)"

poetry-fix:  ## Force pip poetry re-installation
	@pip install poetry --upgrade


# RUN ##################################################################


run: ## Start ocxwiki CLI
	@python cli.py
PHONY: run
# TESTS #######################################################################

FAILURES := .pytest_cache/pytest/v/cache/lastfailed

test:  ## Run unit and integration tests
	#@pytest --durations=5  --cov-report html --cov src .
	@pytest

test-upd:  ## Update the regression tests baseline
	@pytest --force-regen

tu: test-upd
PHONY: tu

test-cov:  ## Show the test coverage report
	cmd /c start $(CURDIR)/$(COVDIR)/index.html

tc: test-cov
.PHONY: tc

PHONY: test-upd, test-cov
# CHECKS ######################################################################
check-lint:	## Run formatters, linters, and static code security scanners bandit and jake
	@printf "\n${BLUE}Running black against source and test files...${NC}\n"
	@black . -v
	@printf "${BLUE}\nRunning Flake8 against source and test files...${NC}\n"
	@flake8 -v


# BUILD #######################################################################

build-exe:   ## Build a bundled package (on windows: an exe file) executable using pyinstaller
	@pyinstaller main.spec
.PHONY: build-exe


# HELP ########################################################################


.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

#-----------------------------------------------------------------------------------------------



