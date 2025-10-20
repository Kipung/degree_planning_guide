# This is a comment
dev:
	docker-compose up -d --build
dev-log:
	docker-compose up --build

start:
	docker-compose up -d
start-log:
	docker-compose up

devstop:
	docker-compose down
devclean:
	docker-compose down --volumes --remove-orphans

log:
	docker-compose logs
logf:
	docker-compose logs -f

restart:
	docker-compose down && docker-compose up -d --build

restart-log:
	docker-compose down && docker-compose up --build
