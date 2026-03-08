.PHONY: install uninstall dev test

install:
	uv tool install --force .

uninstall:
	uv tool uninstall ztrace

dev:
	uv sync

test:
	uv run ztrace summary test/fixtures/sample.trace
