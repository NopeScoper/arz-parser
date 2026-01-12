import requests
from bs4 import BeautifulSoup
import re
import json

def parse_price_data(price_str):
    """
    Разбирает строку вида: '304руб.499руб.Скидка 39%' или '59az.85az.Скидка 30%'
    Возвращает: (цена, старая_цена, процент, валюта)
    """
    # Чистим строку от мусора
    clean_str = price_str.replace('\xa0', '').replace(' ', '').lower().replace('\n', '')
    
    # Определяем валюту
    currency = "AZ"
    if "руб" in clean_str:
        currency = "Руб."
    elif "az" in clean_str:
        currency = "AZ"

    # Ищем все числа в строке
    # Регулярка ищет группы цифр
    numbers = re.findall(r'(\d+)', clean_str)
    
    current_val = 0
    old_val = 0
    percent = 0

    if len(numbers) >= 3:
        # [Цена, СтараяЦена, Процент] -> 304, 499, 39
        current_val = int(numbers[0])
        old_val = int(numbers[1])
        percent = int(numbers[2])
    elif len(numbers) == 2:
        # [Цена, Процент] -> 304, 39 (если старой цены нет)
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
    
    # Словарь для лучших предложений
    best_deals = {}

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            
            # На сайте таблица имеет 5 колонок:
            # 0: Название
            # 1: Категория
            # 2: Сервер
            # 3: Скидки (Цены)
            # 4: Временный (Дата)
            if not cols or len(cols) < 5:
                continue

            # Извлекаем текст и чистим от пробелов
            item_name = cols[0].text.strip().replace('\xa0', ' ')
            category = cols[1].text.strip().replace('\xa0', ' ')
            server_str = cols[2].text.strip().replace('\xa0', ' ')
            price_raw = cols[3].text.strip()
            date_str = cols[4].text.strip().replace('\xa0', ' ')

            # Парсим цены
            price, old_price, percent, currency = parse_price_data(price_raw)

            # Формируем красивую цену для отображения
            display_price = f"{price} {currency}"

            # Данные для сохранения
            item_data = {
                'name': item_name,
                'category': category,      # <-- Добавлено
                'server': server_str,
                'price_val': price,
                'old_price': old_price,    # <-- Добавлено
                'percent': percent,        # <-- Добавлено
                'currency': currency,
                'display_price': display_price,
                'time_str': date_str       # <-- Добавлено (Дата окончания)
            }

            # Логика: если предмета нет в списке ИЛИ новая цена ниже сохраненной
            if item_name not in best_deals:
                best_deals[item_name] = item_data
            else:
                # Если нашли цену дешевле, обновляем запись
                if price < best_deals[item_name]['price_val']:
                    best_deals[item_name] = item_data

    # Сортируем список по названию
    result_list = list(best_deals.values())
    result_list.sort(key=lambda x: x['name'])

    # Сохраняем в JSON
    with open('discounts.json', 'w', encoding='utf-8') as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)
    
    print(f"Успешно! Обработано {len(result_list)} товаров. Добавлены категории и время.")

if __name__ == "__main__":
    get_arz_discounts()
