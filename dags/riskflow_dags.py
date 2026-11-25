"""DAGs do RiskFlow.

riskflow_daily  - todo dia processa o dia anterior: extract -> stage (+ qualidade) -> mart -> score
riskflow_train  - toda semana re-treina o modelo com todo o mart

As tasks so chamam as funcoes de pipeline/steps.py; a logica fica fora do Airflow e e
testavel sem ele. Backfill de um periodo:
    airflow backfill create --dag-id riskflow_daily --from-date 2026-10-03 --to-date 2026-10-06
(processa de 02/10 a 05/10: cada execucao trata o dia anterior a sua data logica)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from airflow.sdk import dag, get_current_context, task
from airflow.sdk.exceptions import AirflowSkipException

DEFAULT_ARGS = {"retries": 2, "retry_delay": timedelta(minutes=1)}


def _target_day() -> date:
    """Dia a processar: o dia completo anterior ao momento da execucao.

    Usa o fim do intervalo menos 1 dia, o que funciona tanto com o timetable padrao do
    Airflow 3 (CronTriggerTimetable, intervalo vazio na hora do disparo) quanto com
    intervalos de dados classicos. Uma execucao disparada em 03/10 00:00 processa 02/10.
    """
    ctx = get_current_context()
    run_time = ctx.get("data_interval_end") or ctx.get("logical_date")
    if run_time is None:  # execucao manual sem data logica
        return date.today() - timedelta(days=1)
    return run_time.date() - timedelta(days=1)


@dag(
    dag_id="riskflow_daily",
    schedule="@daily",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    # Features de um dia dependem do historico dos anteriores: um dia por vez, em ordem.
    # max_active_runs vale para o agendador; depends_on_past garante a ordem tambem
    # em backfills, que no Airflow 3 tem limite de paralelismo proprio.
    max_active_runs=1,
    default_args={**DEFAULT_ARGS, "depends_on_past": True},
    tags=["riskflow"],
)
def riskflow_daily():
    @task
    def extract_load_raw() -> int:
        from pipeline import steps

        return steps.extract_and_load_raw(_target_day())

    @task(retries=0)  # falha de qualidade nao se resolve tentando de novo
    def stage_with_quality_checks() -> int:
        from pipeline import steps

        return steps.stage(_target_day())

    @task
    def build_mart() -> int:
        from pipeline import steps

        return steps.build_mart(_target_day())

    @task
    def score() -> int:
        from ml.model import ModelNotTrainedError
        from pipeline import steps

        try:
            return steps.score(_target_day())
        except ModelNotTrainedError as exc:
            raise AirflowSkipException("Sem modelo treinado ainda; rode a DAG riskflow_train.") from exc

    extract_load_raw() >> stage_with_quality_checks() >> build_mart() >> score()


@dag(
    dag_id="riskflow_train",
    schedule="@weekly",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["riskflow", "ml"],
)
def riskflow_train():
    # Treino em processo Python isolado (mesmo comando da CLI). Dentro do processo do
    # Airflow o modulo `dill` altera o pickler global e o modelo salvo passaria a
    # depender dele, quebrando o carregamento na API de inferencia.
    @task.bash
    def train() -> str:
        return "python -m pipeline.run train"

    train()


riskflow_daily()
riskflow_train()
