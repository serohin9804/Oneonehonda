from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_renders_without_fabricating_market_data():
    app = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert any("не удалось подтвердить объявления" in item.value.lower() for item in app.warning)


if __name__ == "__main__":
    test_app_renders_without_fabricating_market_data()
    print("smoke test passed")
