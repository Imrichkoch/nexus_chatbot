import importlib.util
import io
from pathlib import Path
import tarfile

import pytest

spec = importlib.util.spec_from_file_location('release', Path(__file__).resolve().parents[1] / 'deploy/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.mark.parametrize('name,kind', [('../outside', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE),
                                     ('nexus/link', tarfile.SYMTYPE), ('data/nexus.sqlite3', tarfile.REGTYPE)])
def test_release_rejects_unsafe_archive_before_extracting(tmp_path, name, kind):
    path = tmp_path / 'bad.tar'
    with tarfile.open(path, 'w') as archive:
        entry = tarfile.TarInfo(name)
        entry.type = kind
        entry.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
        archive.addfile(entry, io.BytesIO(b''))
    with pytest.raises(ValueError):
        release.unpack(path, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_failed_environment_switch_restores_previous_code_and_dependencies(tmp_path, monkeypatch):
    import sys

    root = tmp_path / 'application'
    (root / 'nexus').mkdir(parents=True)
    (root / 'nexus/app.py').write_text('previous code')
    (root / '.venv').mkdir()
    (root / '.venv/version').write_text('previous dependencies')
    bundle = tmp_path / 'release.tar'
    with tarfile.open(bundle, 'w') as archive:
        for name, content in [('nexus/app.py', b'new code'), ('requirements.txt', b'')]:
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))
    calls = []
    monkeypatch.setattr(release, 'run', lambda *args, **kwargs: calls.append(args))
    def fail_switch(*args, **kwargs):
        raise OSError('Simulated environment switch failure')
    monkeypatch.setattr(Path, 'symlink_to', fail_switch)
    monkeypatch.setattr(sys, 'argv', ['release.py', str(bundle), '--app-root', str(root)])
    with pytest.raises(OSError, match='Simulated'):
        release.main()
    assert (root / 'nexus/app.py').read_text() == 'previous code'
    assert (root / '.venv/version').read_text() == 'previous dependencies'
    assert calls[-1] == ('systemctl', 'start', 'nexuschat.service')
