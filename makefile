bump:
	@echo "Bumping huddle01-ai version"
	@poetry version patch
	@echo "Bumped huddle01-ai version"

pre-bump:
	@echo "Bumping Version to Pre-release"
	@poetry version prerelease
	@echo "Bumped Version to Pre-release"

publish:
	@echo "Publishing huddle01-ai to PyPi"
	@rm -rf dist
	@poetry build
	@poetry publish
	@echo "Published huddle01-ai to PyPi"

fmt:
	@echo "Formatting huddle01-ai code"
	@poetry run python -m ruff format
	@echo "Formatted huddle01-ai code"

fix:
	@echo "Checking huddle01-ai code"
	@poetry run python -m ruff check --fix
	@echo "Checked huddle01-ai code"

test:
	@echo "Running huddle01-ai tests"
	@poetry run python -m tests.main

chatbot:
	@echo "Running huddle01-ai chatbot example"
	@poetry run python -m example.chatbot.main

gtext:
	@echo "Running huddle01-ai gemini text"
	@poetry run python -m example.gemini.textchat

gmulti:
	@echo "Running huddle01-ai gemini realtime"
	@poetry run python -m example.gemini.multimodalchat

gemini:
	@echo "Running huddle01-ai gemini huddle01"
	@poetry run python -m example.gemini.main

run:
	@echo "Running huddle01-ai conference example"
	@poetry run python -m example.chatbot.main

.PHONY: publish run bump pre-bump
