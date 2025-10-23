import os
import shutil
import sqlite3

import pandas as pd
import requests

db_url = "https://storage.googleapis.com/benchmarks-artifacts/travel-db/travel2.sqlite"
local_file = "travel2.sqlite"
backup_file = "travel2.backup.sqlite"


def setup_database():
    """Descarga y prepara la base de datos SQLite."""
    if os.path.exists(local_file) and os.path.getsize(local_file) == 0:
        os.remove(local_file)

    if not os.path.exists(local_file):
        print("Descargando base de datos...")
        response = requests.get(db_url)
        response.raise_for_status()
        with open(local_file, "wb") as f:
            f.write(response.content)
        print(f"Base de datos descargada: {len(response.content)} bytes")
        shutil.copy(local_file, backup_file)

    if os.path.getsize(local_file) == 0:
        raise ValueError("La base de datos descargada está vacía")

    conn = sqlite3.connect(local_file)

    tables = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table';", conn
    ).name.tolist()

    print(f"Tablas encontradas: {tables}")

    if not tables:
        raise ValueError("No se encontraron tablas en la base de datos")

    tdf = {}
    for t in tables:
        tdf[t] = pd.read_sql(f"SELECT * from {t}", conn)
        print(f"Tabla '{t}': {len(tdf[t])} filas")

    if "flights" not in tdf:
        raise KeyError(f"La tabla 'flights' no existe. Tablas disponibles: {list(tdf.keys())}")

    example_time = pd.to_datetime(
        tdf["flights"]["actual_departure"].replace("\\N", pd.NaT)
    ).max()
    current_time = pd.to_datetime("now").tz_localize(example_time.tz)
    time_diff = current_time - example_time

    tdf["bookings"]["book_date"] = (
        pd.to_datetime(tdf["bookings"]["book_date"].replace("\\N", pd.NaT), utc=True)
        + time_diff
    )

    datetime_columns = [
        "scheduled_departure",
        "scheduled_arrival",
        "actual_departure",
        "actual_arrival",
    ]
    for column in datetime_columns:
        tdf["flights"][column] = (
            pd.to_datetime(tdf["flights"][column].replace("\\N", pd.NaT)) + time_diff
        )

    for table_name, df in tdf.items():
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()
    print("Fechas actualizadas correctamente.")
    return local_file


if __name__ == "__main__":
    setup_database()
    print("Configuración de la base de datos completada.")
