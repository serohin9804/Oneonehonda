from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).parent


def test_dataset_is_real_scoped_and_deduplicated():
    df = pd.read_csv(ROOT / "data" / "listings.csv")
    assert len(df) == 22
    assert df["id"].is_unique
    assert df["published_date"].between("2026-09-12", "2026-09-25").all()
    assert df[["year", "price_usd", "mileage_km"]].notna().all().all()
    assert int(df["duplicate_suspected"].sum()) == 3
    assert int(df["condition"].eq("repair").sum()) == 1
    normal_unique = df[~df["duplicate_suspected"] & df["condition"].ne("repair")]
    assert len(normal_unique) == 18


def test_streamlit_page_runs_with_real_data():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value.startswith("Honda M-NV")
    assert len(app.get("plotly_chart")) == 1


if __name__ == "__main__":
    test_dataset_is_real_scoped_and_deduplicated()
    test_streamlit_page_runs_with_real_data()
    print("2 tests passed")
