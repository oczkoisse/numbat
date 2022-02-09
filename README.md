numbat
======

numbat is a tool that allows annotating multiple videos at the same time.

Features
--------

* Supports synchronized labeling of up to 4 videos
* OpenGL based hardware-accelerated video rendering
* Supports virtually unlimited annotation streams

Develop
-------

1. Clone the repository
2. Install developer dependencies: `pip install -e .[dev]`
3. Install pre-commit Git hooks: `pre-commit install`
4. (Optional) Install recommended extensions for workspace in VSCode

Testing
-------

* To test against editable installation, run `pytest tests/`
* Optionally, one may choose to also generate test coverage data while testing: `pytest --cov=numbat --cov-report=xml tests/`
* To test package installation for multiple Python versions, run `tox`
