"""Falha se alguma DAG tiver erro de importacao. Roda dentro da imagem do Airflow (CI)."""

from airflow.dag_processing.dagbag import DagBag

bag = DagBag("/opt/riskflow/dags")
if bag.import_errors:
    raise SystemExit(f"Erros de importacao: {bag.import_errors}")
print("DAGs OK:", sorted(bag.dags))
