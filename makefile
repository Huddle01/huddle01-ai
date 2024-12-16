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

test:
	@echo "Running huddle01-ai tests"
	@poetry run python -m tests.main

chatbot:
	@echo "Running huddle01-ai chatbot example"
	@poetry run python -m example.chatbot.main

gemini:
	@echo "Running huddle01-ai gemini example"
	@poetry run python -m example.gemini.main

voice:
	@echo "Running huddle01-ai gemini example"
	@poetry run python -m example.gemini.voicechat

run:
	@echo "Running huddle01-ai conference example"
	@poetry run python -m example.chatbot.main

.PHONY: publish run bump pre-bump