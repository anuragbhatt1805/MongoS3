.PHONY: help build run test scout clean

IMAGE_NAME ?= anuragbhatt1805/mongos3:latest

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the custom Docker image
	docker build -t $(IMAGE_NAME) .

run: ## Run backup using local .env file
	docker run --rm --env-file .env $(IMAGE_NAME)

test: ## Execute automated end-to-end integration test suite
	chmod +x tests/run_e2e_test.sh
	./tests/run_e2e_test.sh

scout: ## Run Docker Scout vulnerability analysis
	docker scout quickview $(IMAGE_NAME)

clean: ## Clean up temporary test containers and dangling images
	docker rm -f $$(docker ps -a -q --filter name=test-mongo) 2>/dev/null || true
	docker rm -f $$(docker ps -a -q --filter name=test-mocks3) 2>/dev/null || true
	docker network rm $$(docker network ls -q --filter name=mongo-test-net) 2>/dev/null || true
