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
st.caption("Объявления, впервые опубликованные за последние 14 дней. Цена и пробег — по данным объявлений.")

@st.cache_data
def load_data() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else pd.DataFrame()
    metadata = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
    for col in ("year", "price", "mileage_km"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df, metadata


df, metadata = load_data()
collected = metadata.get("collected_at", "не указано")
period = metadata.get("period", "не указан")
st.info(f"**Снимок данных:** {collected} · **Период публикации:** {period}. Данные — объявления, найденные и проверенные на площадках; это не официальный реестр сделок.")

if df.empty:
    st.warning("В проверенных источниках не удалось подтвердить объявления Honda M-NV с датой публикации в выбранном 14-дневном окне. График не строится, чтобы не подменять рыночные данные примерными значениями.")
    st.markdown("### Проверенные источники")
    sources = metadata.get("sources", [])
    if sources:
        for source in sources:
            st.write(f"- {source.get('name', 'Источник')}: {source.get('result', 'проверен')} — [открыть поиск]({source.get('url', '#')})")
    st.caption("Объявления могут появляться и исчезать; повторная проверка нужна для актуализации снимка.")
    st.stop()

required = {"title", "year", "price", "currency", "mileage_km", "published_date", "city", "source", "url"}
missing = required - set(df.columns)
if missing:
    st.error("В файле данных отсутствуют обязательные поля: " + ", ".join(sorted(missing)))
    st.stop()

df["published_date"] = pd.to_datetime(df["published_date"], errors="coerce").dt.date
if "evidence" not in df.columns:
    df["evidence"] = ""

currencies = sorted(df["currency"].dropna().astype(str).unique().tolist())
with st.sidebar:
    st.header("Фильтры")
    selected_currency = st.selectbox("Валюта цены", currencies)
    view = df[df["currency"].astype(str) == selected_currency].copy()
    years = sorted(view["year"].dropna().astype(int).unique().tolist())
    selected_years = st.multiselect("Год выпуска", years, default=years)
    if selected_years:
        view = view[view["year"].isin(selected_years)]
    sources = sorted(view["source"].dropna().astype(str).unique().tolist())
    selected_sources = st.multiselect("Площадка", sources, default=sources)
    if selected_sources:
        view = view[view["source"].isin(selected_sources)]

if view.empty:
    st.warning("Для выбранных фильтров объявлений нет.")
    st.stop()

valid_price = view["price"].dropna()
valid_mileage = view["mileage_km"].dropna()
a, b, c, d = st.columns(4)
a.metric("Объявлений", f"{len(view)}")
b.metric("Медианная цена", f"{valid_price.median():,.0f} {selected_currency}".replace(",", " ") if len(valid_price) else "—")
c.metric("Медианный пробег", f"{valid_mileage.median():,.0f} км".replace(",", " ") if len(valid_mileage) else "—")
years_in_view = view["year"].dropna().astype(int)
d.metric("Годы выпуска", f"{years_in_view.min()}–{years_in_view.max()}" if len(years_in_view) else "—")

st.subheader(f"Цена и пробег · {selected_currency}")
chart_df = view.dropna(subset=["price", "mileage_km"])
if chart_df.empty:
    st.warning("Недостаточно данных о цене и пробеге для графика.")
else:
    fig = px.scatter(
        chart_df,
        x="mileage_km",
        y="price",
        color="year",
        symbol="source",
        hover_name="title",
        hover_data={"mileage_km": ":,.0f", "price": ":,.0f", "year": True,
                    "published_date": True, "city": True, "source": True,
                    "url": True, "currency": False},
        labels={"mileage_km": "Пробег, км", "price": f"Цена, {selected_currency}",
                "year": "Год выпуска", "source": "Площадка"},
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    fig.update_layout(height=540, legend_title_text="Год выпуска / площадка", margin=dict(l=10, r=10, t=20, b=10))
    fig.update_traces(marker=dict(size=13, opacity=0.82, line=dict(width=1, color="white")))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Объявления в выборке")
display = view[["published_date", "title", "year", "price", "currency", "mileage_km", "city", "source", "url"]].copy()
display = display.rename(columns={"published_date": "Опубликовано", "title": "Объявление", "year": "Год", "price": "Цена", "currency": "Валюта", "mileage_km": "Пробег, км", "city": "Город", "source": "Площадка", "url": "Ссылка"})
st.dataframe(display, hide_index=True, use_container_width=True, column_config={"Ссылка": st.column_config.LinkColumn("Источник", display_text="Открыть объявление")})

if len(valid_price) >= 2:
    st.subheader("Краткая статистика")
    st.write(f"Цены в выбранной валюте: от **{valid_price.min():,.0f}** до **{valid_price.max():,.0f} {selected_currency}**. Медиана рассчитана только по показанным объявлениям; на неё влияют комплектация, состояние, импорт и полнота информации в карточках.".replace(",", " "))

st.caption("Методика: учитываются только объявления Honda M-NV с подтверждённой датой публикации внутри выбранного периода. Валюты показываются раздельно, курс вручную не предполагается. Наблюдаемая цена объявления не равна цене закрытой сделки.")
