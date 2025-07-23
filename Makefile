.PHONY: help setup dev test lint clean build deploy

help: ## Show this help message
	@echo "Romanian Freight Forwarder Automation System"
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Initial project setup
	@echo "🚚 Setting up Romanian Freight Forwarder Automation System..."
	@if [ ! -f .env ]; then \
		cp .env.example .env && \
		echo "✅ Created .env file from template"; \
		echo "⚠️  Please edit .env file with your API keys"; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@echo "📦 Installing backend dependencies..."
	@cd backend && python -m venv venv && \
		. venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt && \
		pip install -r requirements-dev.txt
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "🐳 Starting Docker services..."
	@docker-compose up -d postgres redis minio
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo "✅ Setup complete! Run 'make dev' to start development servers"

dev: ## Start development servers
	@echo "🚀 Starting development environment..."
	@docker-compose up -d
	@echo "✅ All services started!"
	@echo "📊 Service URLs:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)"
	@echo "  PostgreSQL: localhost:5432 (logistics/password)"
	@echo "  Redis: localhost:6379"

stop: ## Stop all development servers
	@echo "🛑 Stopping all services..."
	@docker-compose stop
	@echo "✅ All services stopped!"

test: ## Run all tests
	@echo "🧪 Running backend tests..."
	@cd backend && . venv/bin/activate && pytest tests/ -v --cov=app
	@echo "🧪 Running frontend tests..."
	@cd frontend && npm run test:run

test-backend: ## Run backend tests only
	@cd backend && . venv/bin/activate && pytest tests/ -v --cov=app

test-frontend: ## Run frontend tests only
	@cd frontend && npm run test:run

test-e2e: ## Run end-to-end tests
	@cd frontend && npm run test:e2e

lint: ## Run code linting
	@echo "🔍 Linting backend code..."
	@cd backend && . venv/bin/activate && \
		black app/ && \
		isort app/ && \
		flake8 app/ && \
		mypy app/
	@echo "🔍 Linting frontend code..."
	@cd frontend && npm run lint && npm run type-check

format: ## Format code
	@echo "💄 Formatting backend code..."
	@cd backend && . venv/bin/activate && black app/ && isort app/
	@echo "💄 Formatting frontend code..."
	@cd frontend && npm run format

migration: ## Create new database migration
	@read -p "Enter migration name: " name; \
	cd backend && . venv/bin/activate && alembic revision --autogenerate -m "$$name"

migrate: ## Run database migrations
	@cd backend && . venv/bin/activate && alembic upgrade head

build: ## Build production images
	@echo "🏗️ Building production images..."
	@docker-compose -f docker-compose.prod.yml build

clean: ## Clean up containers and volumes
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@docker system prune -f
	@echo "✅ Cleanup complete!"

logs: ## Show logs from all services
	@docker-compose logs -f

logs-backend: ## Show backend logs
	@docker-compose logs -f backend

logs-frontend: ## Show frontend logs  
	@docker-compose logs -f frontend

logs-db: ## Show database logs
	@docker-compose logs -f postgres

shell-backend: ## Open backend Python shell
	@cd backend && . venv/bin/activate && python

shell-db: ## Open database shell
	@docker-compose exec postgres psql -U logistics logistics_db

backup-db: ## Backup database
	@docker-compose exec postgres pg_dump -U logistics logistics_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created!"

restore-db: ## Restore database from backup
	@read -p "Enter backup file path: " file; \
	docker-compose exec -T postgres psql -U logistics logistics_db < $$file

status: ## Show service status
	@docker-compose ps

health: ## Check service health
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8000/health | jq . || echo "❌ Backend not responding"
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend responding" || echo "❌ Frontend not responding"
	@docker-compose exec postgres pg_isready -U logistics && echo "✅ Database responding" || echo "❌ Database not responding"
	@docker-compose exec redis redis-cli ping && echo "✅ Redis responding" || echo "❌ Redis not responding"
