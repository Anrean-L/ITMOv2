.PHONY: install test step1 step2 step3 step6

install:
	@echo "Для практик 1–2 ничего устанавливать не нужно."

test: step1 step2 step3 step6

step1:
	@$(MAKE) -s -C practices/practice_01 test

step2:
	@$(MAKE) -s -C practices/practice_02 test

step3:
	@$(MAKE) -s -C practices/practice_03 test

step6:
	@$(MAKE) -s -C practices/practice_06 test
