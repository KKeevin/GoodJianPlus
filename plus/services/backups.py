"""SQLite online backup plus media archive, with a verifiable manifest."""
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path


def digest(stream):
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_backup(path):
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as temporary:
        manifest = json.loads(archive.read('manifest.json'))
        if set(archive.namelist()) != set(manifest) | {'manifest.json'}:
            raise ValueError('備份清單不一致')
        for name, checksum in manifest.items():
            with archive.open(name) as stream:
                if digest(stream) != checksum:
                    raise ValueError(f'備份損毀：{name}')
        database = Path(temporary) / 'verify.sqlite3'
        with archive.open('database.sqlite3') as source, database.open('wb') as target:
            import shutil
            shutil.copyfileobj(source, target)
        with closing(sqlite3.connect(database)) as conn:
            if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('SQLite 完整性檢查失敗')
        return len(manifest)


def create_backup(database, media, output):
    database, media, output = Path(database).resolve(), Path(media).resolve(), Path(output).resolve()
    if not database.is_file() or output.is_relative_to(media):
        raise ValueError('資料庫不存在，或備份位置位於 media 內')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / 'database.sqlite3'
        source = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            source.close()
            target.close()
        files = [('database.sqlite3', snapshot)]
        if media.exists():
            files += [(f'media/{p.relative_to(media).as_posix()}', p) for p in media.rglob('*')
                      if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(media)]
        # Exclusive creation prevents accidental overwrite of a previous backup.
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, path in files:
                archive.write(path, name)
        with zipfile.ZipFile(output) as archive:
            manifest = {}
            for name in archive.namelist():
                with archive.open(name) as stream:
                    manifest[name] = digest(stream)
        with zipfile.ZipFile(output, 'a') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
    return verify_backup(output)
