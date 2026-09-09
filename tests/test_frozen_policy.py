import json
import shogi
import pytest

from surprise.human_policy import Policy, describe
from surprise.frozen_policy import encode_model, decode_model, immutable_json


def test_frozen_statistics_roundtrip_without_new_training():
    p=describe(shogi.Board().sfen())
    old=Policy({'positions':{'p':p}},[{'pid':'p','prefix':'','move':'7g7f'}])
    restored=decode_model(json.loads(json.dumps(encode_model(old))))
    for kind in ('hierarchical','behavior','exact','popularity','prefix'):
        assert old.predict(p,'p','',kind,2,1)==restored.predict(p,'p','',kind,2,1)


def test_frozen_file_refuses_overwrite(tmp_path):
    path=tmp_path/'snapshot.json'
    immutable_json(path,{'weights':[1,2]})
    immutable_json(path,{'weights':[1,2]})
    with pytest.raises(ValueError):immutable_json(path,{'weights':[1,3]})
    assert json.loads(path.read_text())=={'weights':[1,2]}
