import requests
from bs4 import BeautifulSoup
import re
import json

def parse_price_data(price_str):
    clean_str = price_str.replace('\xa0', '').replace(' ', '').lower().replace('\n', '')
    
    currency = "AZ"
    if "руб" in clean_str:
        currency = "Руб."
    elif "az" in clean_str:
        currency = "AZ"

    numbers = re.findall(r'(\d+)', clean_str)
    
    current_val = 0
    old_val = 0
    percent = 0

    if len(numbers) >= 3:
        current_val = int(numbers[0])
        old_val = int(numbers[1])
        percent = int(numbers[2])
    elif len(numbers) == 2:
        current_val = int(numbers[0])
        percent = int(numbers[1])
    elif len(numbers) == 1:
        current_val = int(numbers[0])

    return current_val, old_val, percent, currency

def get_arz_discounts():
    url = "https://arz-wiki.com/arz-rp/articles/donate-items-percent/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    print("Подключаюсь к сайту...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all('table')
    
    # Используем словарь, чтобы хранить только уникальные предметы
    # Ключ = Название предмета
    best_deals = {}

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols or len(cols) < 5:
                continue

            item_name = cols[0].text.strip().replace('\xa0', ' ')
            category = cols[1].text.strip().replace('\xa0', ' ')
            server_str = cols[2].text.strip().replace('\xa0', ' ')
            price_raw = cols[3].text.strip()
            date_str = cols[4].text.strip().replace('\xa0', ' ')

            price, old_price, percent, currency = parse_price_data(price_raw)
            display_price = f"{price} {currency}"

            item_data = {
                'name': item_name,
                'category': category,
                'server': server_str,
                'price_val': price,
                'old_price': old_price,
                'percent': percent,
                'currency': currency,
                'display_price': display_price,
                'time_str': date_str
            }

            # ЛОГИКА ЛУЧШЕЙ ЦЕНЫ:
            # 1. Если предмета нет в базе -> добавляем.
            # 2. Если предмет есть, но новая цена НИЖЕ -> перезаписываем (удаляем старый сервер, пишем новый).
            if item_name not in best_deals:
                best_deals[item_name] = item_data
            else:
                if price < best_deals[item_name]['price_val']:
                    best_deals[item_name] = item_data
                    # Тут мы заменили запись. Если раньше было "Сервер 1,2,3", а теперь нашли дешевле на "Сервер 5",
                    # то в базе останется только "Сервер 5".

    result_list = list(best_deals.values())
    result_list.sort(key=lambda x: x['name'])

    with open('discounts.json', 'w', encoding='utf-8') as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)
    
    print(f"Готово! В списке {len(result_list)} самых выгодных товаров.")

if __name__ == "__main__":
    get_arz_discounts()
