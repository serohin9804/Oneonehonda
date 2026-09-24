from pathlib import Path
import pandas as pd

root = Path(__file__).parent
data = pd.read_csv(root / "data" / "listings.csv")
normal = data.loc[~data["duplicate_suspected"] & data["condition"].ne("repair")].copy()
print(f"Всего карточек: {len(data)}")
print(f"Площадки: {data['source'].value_counts().to_dict()}")
print(f"Чистая базовая выборка после исключения вероятных дублей и авто под восстановление: {len(normal)}")
for currency, column in (("USD", "price_usd"), ("UAH", "price_uah")):
    prices = normal[column].dropna()
    mileage = normal.loc[normal[column].notna(), "mileage_km"].dropna()
    if not len(prices):
        continue
    print(f"{currency}: n={len(prices)}, min={prices.min():.0f}, median={prices.median():.0f}, max={prices.max():.0f}, median_mileage_km={mileage.median():.0f}")
print(f"Годы выпуска: {normal['year'].value_counts().sort_index().to_dict()}")
