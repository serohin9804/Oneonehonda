from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "listings.csv"
META_PATH = BASE_DIR / "data" / "metadata.json"

st.set_page_config(page_title="Honda M-NV | рынок Украины", page_icon="🚗", layout="wide")
st.title("Honda M-NV — вторичный рынок Украины")
st.caption("Свежие объявления · опубликованы с 12 по 25 сентября 2026 года · данные карточек, не цены закрытых сделок")

@st.cache_data
def load_data() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else pd.DataFrame()
    metadata = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
    for col in ("year", "price_usd", "price_uah", "mileage_km"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df, metadata


df, metadata = load_data()
st.info(f"**Собрано:** {metadata.get('collected_at', 'не указано')} · **Окно публикации:** {metadata.get('period', 'не указано')}. В таблице сохранены цены и сведения со страниц объявлений.")

if df.empty:
    st.warning("В выборке пока нет подтверждённых объявлений; график не строится, чтобы не подменять рыночные данные примерами.")
    st.stop()

with st.sidebar:
    st.header("Фильтры")
    include_duplicates = st.checkbox("Показать вероятные кросс-посты", value=False, help="Совпадающие по цене, пробегу, году и городу пары оставлены в таблице, но скрыты в базовом сравнении.")
    include_repair = st.checkbox("Включить авто на восстановление", value=False, help="Одна карточка OLX прямо указывает продажу на запчасти/под восстановление, поэтому по умолчанию не включена в сводные цены.")

view = df.copy()
if not include_duplicates and "duplicate_suspected" in view.columns:
    view = view[~view["duplicate_suspected"].fillna(False).astype(bool)]
if not include_repair and "condition" in view.columns:
    view = view[view["condition"].fillna("used") != "repair"]

currency_options = []
if view["price_usd"].notna().any():
    currency_options.append("USD")
if view["price_uah"].notna().any():
    currency_options.append("UAH")
if not currency_options:
    st.warning("Цены отсутствуют в выборке.")
    st.stop()

with st.sidebar:
    currency = st.selectbox("Валюта цены", currency_options, index=0)
    years = sorted(view["year"].dropna().astype(int).unique().tolist())
    selected_years = st.multiselect("Год выпуска", years, default=years)
    sources = sorted(view["source"].dropna().astype(str).unique().tolist())
    selected_sources = st.multiselect("Площадка", sources, default=sources)

price_col = "price_usd" if currency == "USD" else "price_uah"
view["price"] = view[price_col]
view["currency"] = currency
if selected_years:
    view = view[view["year"].isin(selected_years)]
if selected_sources:
    view = view[view["source"].isin(selected_sources)]
view = view.dropna(subset=["price"])
if view.empty:
    st.warning("Для выбранных фильтров нет наблюдений с ценой в этой валюте.")
    st.stop()

valid_price = view["price"].dropna()
valid_mileage = view["mileage_km"].dropna()
a, b, c, d = st.columns(4)
a.metric("Объявлений в выборке", f"{len(view)}")
b.metric("Медианная цена", f"{valid_price.median():,.0f} {currency}".replace(",", " "))
c.metric("Медианный пробег", f"{valid_mileage.median():,.0f} км".replace(",", " ") if len(valid_mileage) else "—")
year_values = view["year"].dropna().astype(int)
d.metric("Годы выпуска", f"{year_values.min()}–{year_values.max()}" if len(year_values) else "—")

st.subheader(f"Цена и пробег · {currency}")
chart_df = view.dropna(subset=["price", "mileage_km"])
if chart_df.empty:
    st.warning("Недостаточно данных о цене и пробеге для графика.")
else:
    chart_data = chart_df.copy()
    chart_data["year"] = chart_data["year"].astype("Int64").astype(str)
    fig = px.scatter(
        chart_data,
        x="mileage_km",
        y="price",
        color="year",
        symbol="source",
        hover_name="title",
        hover_data={"mileage_km": ":,.0f", "price": ":,.0f", "year": True,
                    "published_date": True, "city": True, "source": True,
                    "url": True, "currency": False, "condition_note": True},
        labels={"mileage_km": "Пробег, км", "price": f"Цена, {currency}",
                "year": "Год выпуска", "source": "Площадка"},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_layout(height=540, legend_title_text="Год выпуска / площадка", margin=dict(l=10, r=10, t=20, b=10))
    fig.update_traces(marker=dict(size=13, opacity=0.82, line=dict(width=1, color="white")))
    st.plotly_chart(fig, width="stretch")

st.subheader("Объявления в выборке")
display = view[["published_date", "title", "year", "price", "currency", "mileage_km", "city", "source", "duplicate_suspected", "condition", "url"]].copy()
display = display.rename(columns={"published_date": "Опубликовано", "title": "Объявление", "year": "Год", "price": "Цена", "currency": "Валюта", "mileage_km": "Пробег, км", "city": "Город", "source": "Площадка", "duplicate_suspected": "Возможный кросс-пост", "condition": "Статус", "url": "Ссылка"})
st.dataframe(display, hide_index=True, width="stretch", column_config={"Ссылка": st.column_config.LinkColumn("Источник", display_text="Открыть объявление")})

if len(valid_price) >= 2:
    st.subheader("Краткая статистика")
    st.write(f"Цены в выбранной валюте: **{valid_price.min():,.0f}–{valid_price.max():,.0f} {currency}**, медиана — **{valid_price.median():,.0f} {currency}**. Это цены предложений в отфильтрованной выборке; комплектация, состояние и качество описания различаются.".replace(",", " "))

st.subheader("Источники и методика")
for source in metadata.get("sources", []):
    st.write(f"- [{source['name']}]({source['url']}): {source['result']}.")
st.caption("Включались карточки Honda M-NV с подтверждённой датой публикации в указанном интервале 12–25 сентября (14 календарных дней). Цены в USD и UAH показываются отдельно, без пересчёта по предположительному курсу. Вероятные межплощадочные дубликаты и авто под восстановление можно включить переключателями слева. Снимок собран 25.09.2026 и сам не обновляется при появлении новых объявлений.")
