import json
import stat

import pytest

from apps.common.private_artifacts import write_private_json


def test_json_review_file_is_private_and_never_overwritten(tmp_path):
    path = tmp_path / "review.json"
    write_private_json(str(path), {"review": "pendente"})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == {"review": "pendente"}
    with pytest.raises(FileExistsError):
        write_private_json(str(path), {"review": "inventada"})
    assert json.loads(path.read_text()) == {"review": "pendente"}


def test_review_file_does_not_follow_symlinks(tmp_path):
    original = tmp_path / "original.json"
    original.write_text("private original")
    link = tmp_path / "review.json"
    link.symlink_to(original)
    with pytest.raises(FileExistsError):
        write_private_json(str(link), {})
    assert original.read_text() == "private original"
