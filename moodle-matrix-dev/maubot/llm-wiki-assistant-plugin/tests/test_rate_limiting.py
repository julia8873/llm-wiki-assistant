import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock
from github_client import GitHubRateLimitError
from sync_worker.tasks import sync_repo_task

@pytest.fixture
def mock_rq_job():
    with patch('rq.get_current_job') as mock_get:
        job = MagicMock()
        job.meta = {}
        job.save_meta = MagicMock()
        job.queue = MagicMock()
        mock_get.return_value = job
        yield job

@patch('sync_worker.tasks._async_sync_repo_task')
def test_rate_limiting_requeue(mock_async_task, mock_rq_job):
    # Simular que el loop asíncrono lanza un error de Rate Limit
    mock_async_task.side_effect = GitHubRateLimitError("Fake rate limit", retry_after_seconds=0)

    # Llamar a la tarea sincrona
    sync_repo_task("fake-room", "fake-url", "fake-official")

    # Confirmar que la meta se guardó y actualizó el número de intentos
    assert mock_rq_job.meta.get('rate_limit_retries') == 1
    mock_rq_job.save_meta.assert_called_once()
    
    # Confirmar que hizo enqueue_in
    assert mock_rq_job.queue.enqueue_in.called
    
    # Verificamos que el delay fue 60 (2^0 * 60)
    args, kwargs = mock_rq_job.queue.enqueue_in.call_args
    delay_delta = args[0]
    assert delay_delta.total_seconds() == 60.0

@patch('sync_worker.tasks._async_sync_repo_task')
def test_rate_limiting_requeue_exponential(mock_async_task, mock_rq_job):
    mock_async_task.side_effect = GitHubRateLimitError("Fake rate limit", retry_after_seconds=0)
    
    # Simular que ya ha fallado 2 veces antes
    mock_rq_job.meta['rate_limit_retries'] = 2

    sync_repo_task("fake-room", "fake-url", "fake-official")

    assert mock_rq_job.meta.get('rate_limit_retries') == 3
    
    args, kwargs = mock_rq_job.queue.enqueue_in.call_args
    delay_delta = args[0]
    # 2^2 * 60 = 240
    assert delay_delta.total_seconds() == 240.0

@patch('sync_worker.tasks._async_sync_repo_task')
def test_rate_limiting_fallback_to_opportunistic(mock_async_task, mock_rq_job):
    # Simular que la comprobación oportunista detectó que quedan 300 segundos
    mock_async_task.side_effect = GitHubRateLimitError("Fake rate limit", retry_after_seconds=300)
    
    # Primer fallo (backoff base sería 60)
    sync_repo_task("fake-room", "fake-url", "fake-official")

    args, kwargs = mock_rq_job.queue.enqueue_in.call_args
    delay_delta = args[0]
    # Como 300 > 60, debe haber cogido 300
    assert delay_delta.total_seconds() == 300.0

@patch('sync_worker.tasks._async_sync_repo_task')
def test_generic_error_no_requeue(mock_async_task, mock_rq_job):
    # Un error genérico normal no debe ser capturado para reencolar,
    # debe dejarse propagar para que RQ use su política genérica Retry.
    mock_async_task.side_effect = RuntimeError("Generic 500 error")

    with pytest.raises(RuntimeError):
        sync_repo_task("fake-room", "fake-url", "fake-official")

    assert not mock_rq_job.queue.enqueue_in.called
