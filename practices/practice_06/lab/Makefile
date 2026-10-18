.PHONY: install test run

install:
	@python3 -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'; import sqlite3; print('Standard library only: ready')"

test: install
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v

run:
	python3 service.py
