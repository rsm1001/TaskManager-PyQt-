"""Integration tests for the reusable local Git worktree pool."""

import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from managers.shortcuts.shortcut_manager import ShortcutManager
from services.shortcuts import git_worktree_service
from services.shortcuts.git_worktree_service import GitWorktreeError, GitWorktreeService


def _git(path, *args):
    return subprocess.run(
        ['git', '-C', str(path), *args], text=True, capture_output=True, check=True,
    )


class _DataManager:
    def __init__(self, shortcut_manager):
        self.shortcut_manager = shortcut_manager
        self._config = {}

    def get_config(self, key, default=''):
        return self._config.get(key, default)

    def set_config(self, key, value):
        self._config[key] = value


def _make_repository(tmp_path):
    remote = tmp_path / 'remote.git'
    repository = tmp_path / 'repository'
    subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
    subprocess.run(['git', 'init', '-b', 'main', str(repository)], check=True, capture_output=True)
    _git(repository, 'config', 'user.name', 'TaskManager Test')
    _git(repository, 'config', 'user.email', 'test@example.invalid')
    (repository / 'launch.py').write_text('print("ok")\n', encoding='utf-8')
    _git(repository, 'add', 'launch.py')
    _git(repository, 'commit', '-m', 'initial')
    _git(repository, 'remote', 'add', 'origin', str(remote))
    _git(repository, 'push', '-u', 'origin', 'main')
    return repository


def test_cleanup_non_main_branches_preserves_main_master_and_checked_out_branch(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))

    _git(repository, 'branch', 'master')
    _git(repository, 'branch', 'feature/remove-me')
    _git(repository, 'branch', 'feature/managed-running')
    _git(repository, 'checkout', '-b', 'feature/checked-out')
    managed = manager.create_agent_workspace(
        parent['id'], 'Running agent', str(tmp_path / 'missing-worktree'),
        'feature/managed-running', 'main', 'running-agent',
    )
    manager.update_agent_workspace(managed['id'], runtime_state='running')

    details = service.get_non_main_branches(parent['id'])
    assert details['protected_branches'] == ['main', 'master']
    assert details['branches'] == [
        'feature/checked-out', 'feature/managed-running', 'feature/remove-me'
    ]
    assert details['checked_out'] == ['feature/checked-out', 'feature/managed-running']
    assert details['branch_usage']['feature/checked-out'][0]['is_registered_worktree'] is True
    assert details['branch_usage']['feature/managed-running'][0]['runtime_state'] == 'running'
    assert details['branch_usage']['feature/managed-running'][0]['is_registered_worktree'] is False

    result = service.cleanup_non_main_branches(parent['id'], branches=['feature/remove-me'])
    assert result['deleted'] == ['feature/remove-me']
    assert result['skipped'] == []
    skipped_result = service.cleanup_non_main_branches(
        parent['id'], branches=['feature/checked-out']
    )
    assert skipped_result['deleted'] == []
    assert skipped_result['skipped'][0]['branch'] == 'feature/checked-out'
    assert _git(repository, 'branch', '--list', 'main').stdout.strip()
    assert _git(repository, 'branch', '--list', 'master').stdout.strip()
    assert _git(repository, 'branch', '--list', 'feature/checked-out').stdout.strip()
    assert not _git(repository, 'branch', '--list', 'feature/remove-me').stdout.strip()
    connection.close()


def test_agent_workspace_is_reused_after_verified_merge(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')

    first = service.create_or_reuse_workspace(parent['id'], 'first feature')
    assert first['workspace_reused'] is False
    first_workspace = manager.get_agent_workspace(first['id'])
    assert os.path.isdir(first_workspace['worktree_path'])
    assert first_workspace['state'] == 'active'

    _git(repository, 'merge', '--no-ff', first_workspace['branch_name'], '-m', 'merge first')
    _git(repository, 'push', 'origin', 'main')
    service.recycle_merged_workspace(first['id'])
    recycled = manager.get_agent_workspace(first['id'])
    assert recycled['state'] == 'idle'
    assert recycled['branch_name'] == ''

    second = service.create_or_reuse_workspace(parent['id'], 'second feature')
    assert second['id'] == first['id']
    assert second['workspace_reused'] is True
    assert manager.get_agent_workspace(second['id'])['state'] == 'active'
    connection.close()


def test_quick_workspace_creation_inherits_launcher_and_uses_sibling_directory(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))

    created = service.create_or_reuse_workspace(parent['id'])
    workspace = manager.get_agent_workspace(created['id'])
    profile = manager.get_repository_profile(parent['id'])

    assert profile['launch_script'] == 'launch.py'
    assert os.path.normcase(os.path.dirname(workspace['worktree_path'])) == os.path.normcase(str(tmp_path))
    assert os.path.isdir(workspace['worktree_path'])
    assert workspace['feature_name'].startswith('智能体-')
    connection.close()


def test_file_shortcut_discovers_its_repository_and_inherits_that_script(tmp_path):
    repository = _make_repository(tmp_path)
    script = repository / 'run.bat'
    script.write_text('@echo off\n', encoding='utf-8')
    _git(repository, 'add', 'run.bat')
    _git(repository, 'commit', '-m', 'add launcher')
    _git(repository, 'push', 'origin', 'main')
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository launcher', str(script))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))

    created = service.create_or_reuse_workspace(parent['id'])
    profile = manager.get_repository_profile(parent['id'])

    assert profile['repository_root'] == os.path.normcase(str(repository))
    assert profile['launch_script'] == 'run.bat'
    assert os.path.isfile(os.path.join(
        manager.get_agent_workspace(created['id'])['worktree_path'], 'run.bat',
    ))
    connection.close()


def test_parent_script_overrides_an_old_guessed_profile_launcher(tmp_path):
    repository = _make_repository(tmp_path)
    script = repository / 'run.bat'
    script.write_text('@echo off\n', encoding='utf-8')
    _git(repository, 'add', 'run.bat')
    _git(repository, 'commit', '-m', 'add launcher')
    _git(repository, 'push', 'origin', 'main')
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository launcher', str(script))
    parent = manager.get_all()[0]
    manager.save_repository_profile(parent['id'], str(repository), launch_script='launch.py')
    service = GitWorktreeService(_DataManager(manager))

    service.create_or_reuse_workspace(parent['id'])
    assert manager.get_repository_profile(parent['id'])['launch_script'] == 'run.bat'
    connection.close()


def test_local_base_is_preferred_after_remote_latest_is_checked(tmp_path):
    repository = _make_repository(tmp_path)
    (repository / 'local.txt').write_text('local only\n', encoding='utf-8')
    _git(repository, 'add', 'local.txt')
    _git(repository, 'commit', '-m', 'local integration commit')
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    profile = service.configure_repository(parent['id'], 'launch.py')

    assert service._sync_and_base_ref(profile) == 'main'
    connection.close()


def test_active_workspace_limit_blocks_additional_agent_children(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.set_active_workspace_limit(1)

    service.create_or_reuse_workspace(parent['id'])
    with pytest.raises(GitWorktreeError, match='已达上限（1/1）'):
        service.create_or_reuse_workspace(parent['id'])
    connection.close()


def test_default_active_workspace_limit_is_two(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))

    first = service.create_or_reuse_workspace(parent['id'])
    second = service.create_or_reuse_workspace(parent['id'])
    with pytest.raises(GitWorktreeError, match='已达上限（2/2）'):
        service.create_or_reuse_workspace(parent['id'])

    assert manager.get_by_id(first['id'])['title'] == '🤖 子类 1'
    assert manager.get_by_id(second['id'])['title'] == '🤖 子类 2'
    connection.close()


def test_repository_git_settings_cannot_change_while_workspaces_exist(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    service.create_or_reuse_workspace(parent['id'], 'feature')

    with pytest.raises(GitWorktreeError, match='仍有智能体工作区'):
        service.configure_repository(parent['id'], 'launch.py', remote_name='other')

    # Launch scripts are independent of Git topology and can still be updated.
    profile = service.configure_repository(parent['id'], 'launch.py')
    assert profile['repository_root'] == os.path.normcase(str(repository))
    connection.close()


def test_recycle_uses_verified_base_when_parent_checkout_is_on_another_branch(tmp_path):
    repository = _make_repository(tmp_path)
    _git(repository, 'checkout', '-b', 'release')
    _git(repository, 'push', '-u', 'origin', 'release')
    _git(repository, 'checkout', 'main')

    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py', base_ref='origin/release')
    created = service.create_or_reuse_workspace(parent['id'], 'release feature')
    workspace = manager.get_agent_workspace(created['id'])

    _git(repository, 'checkout', 'release')
    _git(repository, 'merge', '--no-ff', workspace['branch_name'], '-m', 'merge release feature')
    _git(repository, 'push', 'origin', 'release')
    _git(repository, 'checkout', 'main')

    service.recycle_merged_workspace(created['id'])
    assert manager.get_agent_workspace(created['id'])['state'] == 'idle'
    assert _git(repository, 'branch', '--list', workspace['branch_name']).stdout.strip() == ''
    connection.close()


def test_workspace_launch_uses_the_inherited_script_inside_its_worktree(tmp_path, monkeypatch):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    created = service.create_or_reuse_workspace(parent['id'])
    workspace = manager.get_agent_workspace(created['id'])
    terminal = Mock()
    monkeypatch.setattr(git_worktree_service, 'launch_terminal_tab', terminal)

    service.launch_workspace_project(created['id'])

    command = terminal.call_args.args[0]
    assert os.path.normcase(command[-1]) == os.path.normcase(
        os.path.join(workspace['worktree_path'], 'launch.py')
    )
    assert os.path.normcase(terminal.call_args.args[1]) == os.path.normcase(workspace['worktree_path'])
    assert manager.get_agent_workspace(created['id'])['runtime_state'] == 'running'
    connection.close()


def test_workspace_deletion_requires_the_feature_branch_to_be_merged(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    created = service.create_or_reuse_workspace(parent['id'])
    workspace = manager.get_agent_workspace(created['id'])
    (Path(workspace['worktree_path']) / 'feature.txt').write_text(
        'feature\n', encoding='utf-8',
    )
    _git(workspace['worktree_path'], 'add', 'feature.txt')
    _git(workspace['worktree_path'], 'commit', '-m', 'feature work')

    with pytest.raises(GitWorktreeError):
        service.remove_workspace(created['id'])

    assert os.path.isdir(workspace['worktree_path'])
    assert manager.get_agent_workspace(created['id']) is not None
    assert manager.get_by_id(created['id']) is not None
    assert _git(repository, 'branch', '--list', workspace['branch_name']).stdout.strip()
    connection.close()


def test_workspace_deletion_removes_merged_branch_worktree_and_shortcut(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    created = service.create_or_reuse_workspace(parent['id'])
    workspace = manager.get_agent_workspace(created['id'])
    (Path(workspace['worktree_path']) / 'feature.txt').write_text(
        'feature\n', encoding='utf-8',
    )
    _git(workspace['worktree_path'], 'add', 'feature.txt')
    _git(workspace['worktree_path'], 'commit', '-m', 'feature work')
    _git(repository, 'merge', '--no-ff', workspace['branch_name'], '-m', 'merge feature')
    _git(repository, 'push', 'origin', 'main')

    service.remove_workspace(created['id'])

    assert not os.path.exists(workspace['worktree_path'])
    assert not _git(repository, 'branch', '--list', workspace['branch_name']).stdout.strip()
    assert manager.get_agent_workspace(created['id']) is None
    assert manager.get_by_id(created['id']) is None
    connection.close()


def test_workspace_deletion_removes_merged_branch_when_parent_checkout_differs_from_base(tmp_path):
    repository = _make_repository(tmp_path)
    _git(repository, 'checkout', '-b', 'release')
    _git(repository, 'push', '-u', 'origin', 'release')
    _git(repository, 'checkout', 'main')

    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py', base_ref='origin/release')
    created = service.create_or_reuse_workspace(parent['id'], 'release feature')
    workspace = manager.get_agent_workspace(created['id'])

    (Path(workspace['worktree_path']) / 'feature.txt').write_text(
        'feature\n', encoding='utf-8',
    )
    _git(workspace['worktree_path'], 'add', 'feature.txt')
    _git(workspace['worktree_path'], 'commit', '-m', 'feature work')

    # 合并到配置的基线分支后，再让父仓库停留在另一个分支。
    # 这种情况下?``git branch -d`` 会拒绝清理。
    _git(repository, 'checkout', 'release')
    _git(repository, 'merge', '--no-ff', workspace['branch_name'], '-m', 'merge feature')
    _git(repository, 'push', 'origin', 'release')
    _git(repository, 'checkout', 'main')

    service.remove_workspace(created['id'])

    assert not os.path.exists(workspace['worktree_path'])
    assert not _git(repository, 'branch', '--list', workspace['branch_name']).stdout.strip()
    assert manager.get_agent_workspace(created['id']) is None
    assert manager.get_by_id(created['id']) is None
    connection.close()


def test_force_workspace_deletion_discards_unmerged_and_dirty_workspace(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    created = service.create_or_reuse_workspace(parent['id'], 'discard me')
    workspace = manager.get_agent_workspace(created['id'])
    worktree_path = Path(workspace['worktree_path'])
    branch_name = workspace['branch_name']
    (worktree_path / 'uncommitted.txt').write_text('discarded\n', encoding='utf-8')

    result = service.force_remove_workspace(created['id'])

    assert result == {'removed': True, 'forced': True}
    assert not worktree_path.exists()
    assert not _git(repository, 'branch', '--list', branch_name).stdout.strip()
    assert manager.get_agent_workspace(created['id']) is None
    assert manager.get_by_id(created['id']) is None
    connection.close()


def test_workspace_deletion_recovers_a_clean_unregistered_worktree_directory(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    created = service.create_or_reuse_workspace(parent['id'])
    workspace = manager.get_agent_workspace(created['id'])
    worktree_path = Path(workspace['worktree_path'])
    branch_name = workspace['branch_name']

    (worktree_path / 'feature.txt').write_text('feature\n', encoding='utf-8')
    _git(worktree_path, 'add', 'feature.txt')
    _git(worktree_path, 'commit', '-m', 'feature work')
    feature_commit = _git(worktree_path, 'rev-parse', 'HEAD').stdout.strip()
    _git(repository, 'merge', '--no-ff', branch_name, '-m', 'merge feature')

    # Simulate a previously interrupted cleanup: the parent no longer lists
    # this path as a worktree, but an ordinary clean Git checkout remains at
    # the recorded workspace directory.
    _git(repository, 'worktree', 'remove', str(worktree_path))
    replacement = tmp_path / 'replacement-checkout'
    subprocess.run(['git', 'clone', str(repository), str(replacement)], check=True, capture_output=True)
    _git(replacement, 'checkout', '-b', branch_name, feature_commit)
    shutil.move(str(replacement), str(worktree_path))
    assert str(worktree_path).replace('\\', '/').lower() not in _git(
        repository, 'worktree', 'list', '--porcelain',
    ).stdout.replace('\\', '/').lower()

    service.remove_workspace(created['id'])

    assert not worktree_path.exists()
    assert not _git(repository, 'branch', '--list', branch_name).stdout.strip()
    assert manager.get_agent_workspace(created['id']) is None
    assert manager.get_by_id(created['id']) is None
    connection.close()


def test_force_stop_workspace_project_terminates_only_matching_process_trees(tmp_path, monkeypatch):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    created = service.create_or_reuse_workspace(parent['id'])
    manager.update_agent_workspace(created['id'], runtime_state='running')
    commands = []

    def run(command, cwd=None, check=True):
        commands.append((command, check))
        output = '123\n456\ninvalid\n' if command[0] == 'powershell.exe' else ''
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr='')

    monkeypatch.setattr(
        service, '_profile',
        lambda _parent_id: manager.get_repository_profile(parent['id']),
    )
    monkeypatch.setattr(service, '_run', run)
    result = service.force_stop_workspace_project(created['id'])

    assert result == {'terminated_processes': 2}
    assert commands[0][0][:4] == [
        'powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand',
    ]
    assert commands[1:] == [
        (['taskkill', '/PID', '123', '/T', '/F'], False),
        (['taskkill', '/PID', '456', '/T', '/F'], False),
    ]
    assert manager.get_agent_workspace(created['id'])['runtime_state'] == 'stopped'
    connection.close()


def test_recycle_reports_the_files_that_make_a_workspace_dirty(tmp_path):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    service.configure_repository(parent['id'], 'launch.py')
    created = service.create_or_reuse_workspace(parent['id'])
    workspace = manager.get_agent_workspace(created['id'])
    dirty_file = os.path.join(workspace['worktree_path'], 'uncommitted-note.txt')
    with open(dirty_file, 'w', encoding='utf-8') as stream:
        stream.write('unfinished work\n')

    with pytest.raises(GitWorktreeError, match='uncommitted-note\\.txt'):
        service.recycle_merged_workspace(created['id'])
    connection.close()


def test_merge_instruction_is_persistent_and_can_be_restored(tmp_path):
    manager = ShortcutManager(connection=sqlite3.connect(':memory:'))
    data_manager = _DataManager(manager)
    service = GitWorktreeService(data_manager)

    service.set_merge_provider('claude')
    service.set_merge_instruction('合并 {branch} 到 {base_branch}')
    assert service.get_merge_provider() == 'claude'
    assert service.get_merge_instruction() == '合并 {branch} 到 {base_branch}'
    assert service.reset_merge_instruction() == service.DEFAULT_MERGE_INSTRUCTION
    assert service.get_merge_instruction() == service.DEFAULT_MERGE_INSTRUCTION
    with pytest.raises(GitWorktreeError):
        service.set_merge_instruction('合并 {unknown}')
    with pytest.raises(GitWorktreeError):
        service.set_merge_provider('other')


def test_merge_agent_opens_in_parent_repository_with_formatted_instruction(tmp_path, monkeypatch):
    repository = _make_repository(tmp_path)
    connection = sqlite3.connect(':memory:')
    manager = ShortcutManager(connection=connection)
    assert manager.create('todo', 'Repository', str(repository))
    parent = manager.get_all()[0]
    service = GitWorktreeService(_DataManager(manager))
    created = service.create_or_reuse_workspace(parent['id'], 'merge feature')
    workspace = manager.get_agent_workspace(created['id'])
    service.set_merge_instruction('合并 {branch} 到 {base_branch}，工作区 {worktree_path}')
    terminal = Mock()
    monkeypatch.setattr(git_worktree_service, 'build_agent_command', lambda _provider: ['codex.exe'])
    monkeypatch.setattr(git_worktree_service, 'launch_terminal_tab', terminal)

    result = service.launch_merge_agent(created['id'])

    assert terminal.call_args.args[0] == [
        'codex.exe',
        '合并 {} 到 main，工作区 {}'.format(workspace['branch_name'], workspace['worktree_path']),
    ]
    assert os.path.normcase(terminal.call_args.args[1]) == os.path.normcase(str(repository))
    assert result['base_branch'] == 'main'
    connection.close()
