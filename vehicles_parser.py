import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Настройки
BASE_URL = "https://arz-wiki.com/arz-rp/vehicles/"

# Создаем скрапер, который обходит защиту Cloudflare
scraper = cloudscraper.create_scraper()

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_vehicle_page(url):
    try:
        # Используем scraper вместо requests
        response = scraper.get(url)
        
        if response.status_code != 200:
            print(f"[-] Ошибка {response.status_code} при открытии машины: {url}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Название
        title = soup.find('h1', class_='entry-title')
        name = clean_text(title.text) if title else "Unknown"

        # 2. Характеристики
        specs = {}
        rows = soup.find_all('tr')
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) == 2:
                key = clean_text(cols[0].text).replace(':', '')
                val = clean_text(cols[1].text)
                specs[key] = val

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

        # 3. Описание
        content_div = soup.find('div', class_='entry-content')
        description_lines = []
        if content_div:
            # Собираем текст, игнорируя таблицы и скрипты
            for elem in content_div.find_all(['p', 'li']):
                if not elem.find_parent('table'): # Если элемент не внутри таблицы
                    text = clean_text(elem.text)
                    if len(text) > 3 and "Cкорость" not in text:
                        description_lines.append(text)
        
        vehicle_data['description'] = "\n".join(description_lines)

        print(f"[+] Успешно: {name}")
        return vehicle_data

    except Exception as e:
        print(f"[-] Ошибка парсинга {url}: {e}")
        return None

def get_all_vehicles():
    all_vehicles = []
    page = 1
    
    print("Начинаю парсинг машин с помощью CloudScraper...")

    while True:
        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}page/{page}/"
            
        print(f"\n--- Страница {page} [{url}] ---")
        
        try:
            response = scraper.get(url)
            
            # ДИАГНОСТИКА
            if response.status_code != 200:
                print(f"!!! ОШИБКА ДОСТУПА: Код {response.status_code}")
                # Если 404 - значит страницы кончились
                if response.status_code == 404:
                    print("Страницы закончились.")
                    break
                # Если 403 - нас заблокировали
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Более широкий поиск ссылок
            # Ищем любые ссылки, содержащие /vehicles/ в адресе
            links = soup.find_all('a', href=True)
            vehicle_links = []
            
            for link in links:
                href = link['href']
                # Фильтруем ссылки: должны быть на машину, не на страницу, не на категории
                if "/vehicles/" in href and href != BASE_URL and "/page/" not in href and "/category/" not in href:
                    if href not in vehicle_links: # Убираем дубликаты
                        vehicle_links.append(href)

            print(f"Найдено ссылок на странице: {len(vehicle_links)}")
            
            if not vehicle_links:
                print("Машин на странице не найдено. Возможно, конец списка или изменилась верстка.")
                break

            for v_url in vehicle_links:
                data = parse_vehicle_page(v_url)
                if data:
                    all_vehicles.append(data)
                # Задержка, чтобы не забанили
                time.sleep(0.5)

            page += 1
            
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            break

    print(f"\nИТОГ: Всего сохранено {len(all_vehicles)} машин.")
    
    # Сохраняем, даже если список пустой (чтобы видеть ошибку в файле, если надо)
    with open('vehicles.json', 'w', encoding='utf-8') as f:
        json.dump(all_vehicles, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    get_all_vehicles()
