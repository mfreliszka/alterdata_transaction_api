lint:
# mypy vendor_dashboard  # checking types in tests is basically impossible
	ruff check .
	ruff format --check .
# djlint --check vendor_dashboard/

format:
	ruff format .
	ruff check --fix --exit-zero --silent .
# run format again to fix the formatting of the files that were changed by ruff
	ruff format .
# djlint --reformat .

build:
	docker compose up --build

run:
	docker compose up -d

stop:
	docker compose down

