import requests
import sqlite3
import pandas as pd
import time
from datetime import datetime

STATION_INFO_URL = "https://gbfs.urbansharing.com/oslobysykkel.no/station_information.json"
STATION_STATUS_URL = "https://gbfs.urbansharing.com/oslobysykkel.no/station_status.json"

def fetch_live_data():
    try:
        info_res = requests.get(STATION_INFO_URL).json()
        status_res = requests.get(STATION_STATUS_URL).json()

        df_info = pd.DataFrame(info_res['data']['stations'])
        df_status = pd.DataFrame(status_res['data']['stations'])

        df_info = df_info[['station_id', 'name', 'lat', 'lon']]
        df_status = df_status[['station_id', 'num_bikes_available', 'num_docks_available']]

        df_live = pd.merge(df_info, df_status, on='station_id')
        df_live.rename(columns={'num_bikes_available': 'bikes_available', 'num_docks_available': 'docks_available'}, inplace=True)
        df_live['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect('oslo_live.db')
        df_live.to_sql('live_stations', conn, if_exists='replace', index=False)
        conn.close()

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Mise a jour reussie.")
    except Exception as e:
        print(f"Erreur lors de la recuperation : {e}")

if __name__ == "__main__":
    print("Demarrage du flux de donnees API...")
    while True:
        fetch_live_data()
        time.sleep(60) # Mise a jour toutes les minutes