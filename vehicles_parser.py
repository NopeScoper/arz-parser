import requests
from bs4 import BeautifulSoup
import json
import time
import re

# Базовый URL
BASE_URL = "https://arz-wiki.com/arz-rp/vehicles/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def clean_text(text):
    if not text: return ""
    # Убираем лишние пробелы и переносы
    return re.sub(r'\s+', ' ', text).strip()

def parse_vehicle_page(url):
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Название машины (Заголовок H1)
        title = soup.find('h1', class_='entry-title')
        name = clean_text(title.text) if title else "Unknown"

        # 2. Характеристики (обычно в таблице)
        specs = {}
        
        # Ищем все строки таблиц
        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) == 2:
                key = clean_text(cols[0].text).replace(':', '')
                val = clean_text(cols[1].text)
                specs[key] = val

        # Собираем нужные поля из specs (маппинг)
        vehicle_data = {
            'name': name,
            'url': url,
            'speed': specs.get('Cкорость', '-'),
            'speed_tt': specs.get('Cкорость c TT2', '-'),
            'speed_ft': specs.get('Cкорость с ФТ (red)', '-'),
            'accel': specs.get('Разгон', '-'),
            'accel_100': specs.get('Разгона до 100км', '-'),
            'seats': specs.get('Мест в машине', '-'),
            'type': specs.get('Тип', '-'),
            'model_id': specs.get('ID машины', '-'),
            'game_name': specs.get('Игровое имя', '-'),
            'files': specs.get('Файлы', '-')
        }

        # 3. Описание (Сертификат, бонусы и т.д.)
        # Обычно это текст в <div class="entry-content">, исключая таблицу
        content_div = soup.find('div', class_='entry-content')
        description_lines = []
        
        if content_div:
            for elem in content_div.find_all(['p', 'li']):
                text = clean_text(elem.text)
                # Исключаем строки, которые похожи на мусор или заголовки
                if len(text) > 5 and "Cкорость" not in text and "ID машины" not in text:
                    description_lines.append(text)
        
        vehicle_data['description'] = "\n".join(description_lines)

        print(f"[+] Парсинг: {name} (ID: {vehicle_data['model_id']})")
        return vehicle_data

    except Exception as e:
        print(f"[-] Ошибка при парсинге {url}: {e}")
        return None

def get_all_vehicles():
    all_vehicles = []
    page = 1
    
    while True:
        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}page/{page}/"
            
        print(f"\n--- Сканирую страницу {page} ---")
        
        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 404:
                print("Страницы закончились.")
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем ссылки на машины (обычно внутри article или h2.entry-title a)
            articles = soup.find_all('article')
            
            if not articles:
                print("Машины не найдены на странице.")
                break

            links_found = 0
            for article in articles:
                link_tag = article.find('a', href=True)
                if link_tag:
                    vehicle_url = link_tag['href']
                    # Проверяем, что ссылка ведет на машину, а не на категорию
                    if "/vehicles/" in vehicle_url and vehicle_url != BASE_URL:
                        data = parse_vehicle_page(vehicle_url)
                        if data:
                            all_vehicles.append(data)
                            links_found += 1
                        # Небольшая задержка, чтобы не ддосить сайт
                        time.sleep(0.2)
            
            if links_found == 0:
                print("Ссылок на странице больше нет, выход.")
                break

            page += 1
            
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            break

    # Сохраняем результат
    print(f"\nВсего найдено машин: {len(all_vehicles)}")
    with open('vehicles.json', 'w', encoding='utf-8') as f:
        json.dump(all_vehicles, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    get_all_vehicles()
