import json

from fleetpulse.cli import main


def test_generate_train_drift_workflow(tmp_path, capsys):
    """The documented three-step CLI workflow runs end to end."""
    data = tmp_path / "telemetry.csv"
    artifacts = tmp_path / "artifacts"

    main(["generate", "--out", str(data), "--vehicles", "12", "--days", "120", "--seed", "7"])
    assert data.exists()
    assert "Positive label rate" in capsys.readouterr().out

    main(["train", "--data", str(data), "--out", str(artifacts), "--seed", "7"])
    assert (artifacts / "model.joblib").exists()
    assert (artifacts / "anomaly.joblib").exists()
    card = json.loads((artifacts / "model_card.json").read_text())
    assert card["model_name"] in {"logistic_regression", "hist_gradient_boosting"}
    assert "Selected model" in capsys.readouterr().out

    main(["drift", "--data", str(data)])
    out = capsys.readouterr().out
    assert "psi" in out and "engine_temp_c" in out
