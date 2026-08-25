import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from mixins.repo_reader import RepoReader
from sync_worker.tasks import _async_log_interaction_task, _async_sync_repo_task

@pytest.mark.asyncio
async def test_repo_reader_refactor_okf_contract():
    reader = RepoReader({"git": {"github": {"pat_env_var": "GH_PAT"}}}, None, None)
    
    async def mock_run_git(*args, **kwargs):
        if "git log" in args[0]:
            return "Ingesta automatica de conceptos desde fake.md"
        return (0, "", "")
        
    reader._run_git_command = AsyncMock(side_effect=mock_run_git)
    
    with patch("os.path.exists", return_value=True), patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        # Simular process que retorna (stdout, stderr) y returncode
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"", b"")
        process_mock.returncode = 0
        mock_exec.return_value = process_mock
        
        reader.llm_client = AsyncMock()
        reader.llm_client.get_response.return_value = "<file path=\"test.md\">\n---\ntitle: test\n---\ncontenido</file>"
        
        with patch("os.makedirs"), patch("builtins.open"):
            # Probar ingesta
            await reader.ingest_file_okf(b"bytes", "fake.md", {"repo_url": "http://fake", "git_provider": "github"})
        
            # Verificar que se usó la constante correcta
            # Llamadas esperadas a git command incluyen el commit
            commit_calls = [call for call in reader._run_git_command.call_args_list if "git commit -m" in call[0][0]]
            assert any("Ingesta automatica de conceptos desde" in call[0][0] for call in commit_calls)
    
            # Probar reversion
            await reader.revert_last_ingest({"repo_url": "http://fake", "git_provider": "github"})
            commit_calls = [call for call in reader._run_git_command.call_args_list if "Reversion automatica" in call[0][0]]
            assert any("Reversion automatica de la ultima ingesta" in call[0][0] for call in commit_calls)

@pytest.mark.asyncio
async def test_tasks_refactor_okf_contract():
    with patch("sync_worker.tasks.run_git_command", new_callable=AsyncMock) as mock_git:
        mock_git.return_value = (0, "", "")
        with patch("os.makedirs"), patch("builtins.open"), patch("sync_worker.tasks.asegurar_repo_local", AsyncMock()), patch("os.path.exists", return_value=True):
            await _async_log_interaction_task("room1", "repo1", "repo2", {"timestamp": "123"})
            
            add_calls = [call for call in mock_git.call_args_list if call[0][0] == "add"]
            assert any("logs/interacciones/" in call[0][1] for call in add_calls)

    with patch("sync_worker.tasks.run_git_command", new_callable=AsyncMock) as mock_git:
        mock_git.return_value = (0, "", "")
        with patch("os.path.exists", return_value=True), patch("sync_worker.tasks.distributed_repo_lock", AsyncMock):
            pass
