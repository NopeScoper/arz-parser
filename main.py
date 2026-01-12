import requests
from bs4 import BeautifulSoup
import re
import json
import os

def parse_price_value(price_str):
    clean_str = price_str.replace('\xa0', '').replace(' ', '').lower()
    match = re.search(r'(\d+)(az|руб)', clean_str)
    if match:
        return int(match.group(1)), match.group(2)
    return float('inf'), 'unknown'

def get_arz_discounts():
    url = "https://arz-wiki.com/arz-rp/articles/donate-items-percent/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    best_deals = {}

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols or len(cols) < 4:
                continue

            cols_text = [col.text.replace('\xa0', ' ').strip() for col in cols]
            item_name = cols_text[0]
            item_server = cols_text[2]
            price_raw = cols_text[3]
            
            price_val, currency = parse_price_value(price_raw)
            display_price = price_raw.split('.')[0] if '.' in price_raw else price_raw

            if item_name not in best_deals or price_val < best_deals[item_name]['price_val']:
                best_deals[item_name] = {
                    'name': item_name,
                    'price_val': price_val,
                    'display_price': display_price,
                    'server': item_server
                }

    # Превращаем словарь в список
    result_list = list(best_deals.values())
    # Сортируем по имени
    result_list.sort(key=lambda x: x['name'])

    # Сохраняем в JSON
    with open('discounts.json', 'w', encoding='utf-8') as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)
    
    print("Файл discounts.json успешно создан!")

if __name__ == "__main__":
    get_arz_discounts()
