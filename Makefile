.PHONY: help install install-dev test lint format clean docker-build docker-run

help:
	@echo "PyParrot - Docker Pipeline CLI"
	@echo ""
	@echo "Available commands:"
	@echo "  make install       - Install the package"
	@echo "  make install-dev   - Install with development dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code with black"
	@echo "  make clean         - Remove build artifacts"
	@echo "  make docker-build  - Build Docker image for example"
	@echo "  make docker-run    - Run example container"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=pyparrot --cov-report=html

lint:
	flake8 pyparrot tests
	mypy pyparrot

format:
	black pyparrot tests examples

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov

# CLI examples
configure:
	pyparrot configure --name test-pipeline --model gpt-3.5-turbo --sample-rate 16000

build:
	pyparrot build --config examples/config.yaml

start:
	pyparrot start --config examples/config.yaml

stop:
	pyparrot stop --name example-pipeline

evaluate:
	pyparrot evaluate --name example-pipeline --dataset examples/eval_dataset.json --output evaluation_results.json

# Docker examples
docker-build:
	docker build -t pyparrot-example examples/

docker-run:
	docker run -d -p 8000:8000 --name pyparrot-test pyparrot-example

docker-stop:
	docker stop pyparrot-test && docker rm pyparrot-test
