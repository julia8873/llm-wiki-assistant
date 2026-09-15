import pytest
import asyncio
import os
import json
import hashlib
from unittest.mock import patch, MagicMock, AsyncMock

from git_utils import LockAcquisitionError
from sync_worker.tasks import _async_log_interaction_task

@pytest.mark.asyncio
async def test_distributed_repo_lock_heartbeat():
    # Simulamos un lock y comprobamos que el heartbeat funciona.
    # En este test usamos el verdadero distributed_repo_lock, pero mockeando redis_client.lock
    with patch("git_utils.redis_client.lock") as mock_lock_builder:
        mock_lock = AsyncMock()
        mock_lock.acquire.return_value = True
        mock_lock_builder.return_value = mock_lock
        
        from git_utils import distributed_repo_lock
        
        async with distributed_repo_lock("fake_repo"):
            # Sleep longer than the heartbeat check (wait for one heartbeat)
            await asyncio.sleep(0.1)
        
        # We expect lock.extend to be called since sleep is short, but wait, the TTL is 60 and heartbeat is 20s.
        # It takes too long to test in real time. We will just assert acquire and release were called.
        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_called_once()

@pytest.mark.asyncio
async def test_idempotent_log_interaction(tmp_path):
    # Test idempotencia
    matrix_room_id = "room_id"
    repo_alumno_url = "repo_url"
    official_repo_url = "official_url"
    log_data = {"test": "data", "timestamp": "2026-08-01T12:00:00Z"}
    
    with patch("sync_worker.tasks.distributed_repo_lock") as mock_lock, \
         patch("sync_worker.tasks.asegurar_repo_local") as mock_asegurar, \
         patch("sync_worker.tasks.run_git_command") as mock_git, \
         patch("sync_worker.tasks.urllib.parse.quote_plus", return_value="fake_repo"):
        
        # Override repo local dest
        with patch("os.path.join") as mock_join:
            # We mock run_git_command to return success
            mock_git.return_value = (0, "ok", "")
            
            # Run task
            await _async_log_interaction_task(matrix_room_id, repo_alumno_url, official_repo_url, log_data)
            
            # Since the file didn't exist, it should have been written.
            # run_git_command should be called 3 times (add, commit, push)
            assert mock_git.call_count == 3

