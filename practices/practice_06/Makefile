.PHONY: install step6 test run

install:
	@$(MAKE) -s -C lab install

step6: install
	@python3 -c "from pathlib import Path; [compile(p.read_bytes(), str(p), 'exec') for p in Path('lab').glob('*.py')]; print('Python sources: OK')"

test:
	@$(MAKE) -s -C lab test

run:
	@$(MAKE) -s -C lab run
