.PHONY: install extract transform run airflow-init airflow-run clean

AIRFLOW_HOME := $(shell pwd)/airflow
DBT_DIR := dbt_project

install:
	uv sync

extract:
	uv run python extract/extract.py

transform:
	cd $(DBT_DIR) && uv run dbt run --profiles-dir .

run:
	AIRFLOW_HOME=$(AIRFLOW_HOME) uv run airflow dags test crypto_elt_pipeline

airflow-init:
	AIRFLOW_HOME=$(AIRFLOW_HOME) uv run airflow db init

airflow-webserver:
	AIRFLOW_HOME=$(AIRFLOW_HOME) uv run airflow webserver --port 8080

airflow-scheduler:
	AIRFLOW_HOME=$(AIRFLOW_HOME) uv run airflow scheduler

clean:
	rm -f data/crypto.duckdb
	cd $(DBT_DIR) && uv run dbt clean