"""Shared prose for human-facing reports; internal IDs remain unchanged in data."""
from __future__ import annotations

HUMAN_DESCRIPTIONS = {
    "actual_candidate": "奇襲手として人間が検討する価値がある指し手",
    "diagnostic_counterexample": "人間の応手予測モデルの問題点を確認するために残している検査用の指し手",
    "control": "通常の指し手に対する予測が補正後も崩れていないか確認するための指し手",
    "fallback": "同じ局面の実例が足りないときに、より一般的な局面での人間の指し手傾向から確率を推定する方法",
    "shrinkage": "同じ局面の実例と一般的な指し手傾向を、実例数に応じて混ぜて予測する方法",
    "tilt": "駒取りや取り返しなどの特徴に応じて、元の予測確率を補正する処理",
}


def classification_sentence(classification: str, candidate_move: str | None = None) -> str:
    if classification == "diagnostic_counterexample":
        return (f"この{candidate_move or '指し手'}は奇襲手の候補ではない。明白な応手を人間の応手予測モデルが"
                "適切に扱えるか確認するために残している。")
    if classification == "control":
        return "この指し手は、通常の序盤局面に対する応手予測が補正後も不自然になっていないか確認するために使っている。"
    return "この指し手は、奇襲手として成立する可能性があるため人間による確認対象にしている。"


def support_sentence(value: int | None) -> str:
    if value is None:
        return "この局面と同じ局面を学習データで観測した回数：不明。"
    suffix = "同じ局面の実例が非常に少ないため、人間の応手確率の推定は信用しすぎない方がよい。" if value < 2 else ""
    return f"この局面と同じ局面を学習データで観測した回数：{value}回。{suffix}"


def probability_difference_sentence(observed: float, predicted: float) -> str:
    points = (predicted - observed) * 100
    direction = "高く" if points > 0 else "低く"
    return (f"実際に選ばれた割合は{observed:.1%}、モデルが予測した割合は{predicted:.1%}だった。"
            f"モデルは実際の選択率を約{abs(points):.1f}ポイント{direction}予測している。")


def freeze_sentence() -> str:
    return "この検証では、新しい検証データを見る前にモデル・係数・判定基準を決め、検証結果を見た後の再調整は行っていない。"


def abstain_sentence(reason: str = "同じ局面の実例が少なく、人間の応手確率を十分な精度で推定できないため") -> str:
    return f"奇襲手として有望かどうかの判定：保留。理由：{reason}。"


FEATURE_DESCRIPTIONS = {
    "capture_any": "何らかの駒を取る応手",
    "material_recovery": "駒得を取り返そうとする応手",
    "high_value_capture": "価値の高い駒を取る応手",
    "promotion": "成りを含む応手",
}


def feature_set_sentence(value: str) -> str:
    names = [FEATURE_DESCRIPTIONS.get(x.strip(), x.strip()) for x in value.split(",") if x.strip()]
    return "、".join(names) if names else "該当する特徴はない"
