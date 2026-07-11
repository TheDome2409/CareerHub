from pathlib import Path


STREAMLIT_APP = Path(
    "src/jobagent/ui/streamlit_app.py"
)


def test_streamlit_app_bootstraps_src_path_before_jobagent_imports():
    source = STREAMLIT_APP.read_text(
        encoding="utf-8"
    )

    src_insert_index = source.index(
        "sys.path.insert"
    )
    first_jobagent_import = source.index(
        "from jobagent."
    )

    assert "Path(__file__).resolve().parents[3]" in source
    assert "SRC = ROOT / \"src\"" in source
    assert src_insert_index < first_jobagent_import
