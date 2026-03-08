from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import sys
import os

# Make sure our extract module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="crypto_elt_pipeline",
    description="Extract Bitcoin prices from CoinGecko, load into DuckDB, transform with dbt",
    default_args=default_args,
    start_date=datetime(2026, 3, 1),
    schedule="@daily",
    catchup=False,  # don't backfill past runs
    tags=["crypto", "elt"],
) as dag:

    def run_extraction():
        from extract.extract import extract_and_load
        extract_and_load()

    extract_task = PythonOperator(
        task_id="extract_and_load",
        python_callable=run_extraction,
    )

    transform_task = BashOperator(
        task_id="dbt_transform",
        bash_command="cd /home/fz/crypto-elt/dbt_project && dbt run --profiles-dir .",
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
        },
    )

    # Define order: extract first, then transform
    extract_task >> transform_task