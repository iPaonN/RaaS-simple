.PHONY: install run test clean dev

# Install dependencies
install:
	pip install -r requirements.txt

# Run the bot
run:
	python bot.py

# Run in development mode (with auto-reload would require additional setup)
dev:
	python bot.py

# Clean Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Setup environment (first time)
setup:
	python -m venv .venv
	@echo "Virtual environment created. Activate it with:"
	@echo "  source .venv/bin/activate  (Linux/Mac)"
	@echo "  .venv\\Scripts\\activate     (Windows)"
	@echo "Then run: make install"

# Check if .env exists
check-env:
	@test -f .env || (echo "❌ .env file not found! Copy .env.example to .env and configure it." && exit 1)
	@echo "✅ .env file found"

# Help
help:
	@echo "Available commands:"
	@echo "  make setup       - Create virtual environment"
	@echo "  make install     - Install dependencies"
	@echo "  make run         - Run the bot"
	@echo "  make check-env   - Check if .env file exists"
	@echo "  make clean       - Clean Python cache files"
