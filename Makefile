.PHONY: test example server zip

test:
	python -m unittest discover -s tests

example:
	python examples/local_runtime.py

server:
	uvicorn uap.server:app --reload

zip:
	cd .. && zip -r uap-reference.zip uap-reference -x 'uap-reference/.venv/*' 'uap-reference/__pycache__/*'
