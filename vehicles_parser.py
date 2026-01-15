import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Настройки
BASE_DOMAIN = "https://arz-wiki.com"
BASE_URL = "https://arz-wiki.com/arz-rp/vehicles/"

scraper = cloudscraper.create_scraper()

def clean_text(text):
    if not text: return ""
    # Убираем лишние пробелы и переносы
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fix_vehicle_name(raw_name):
    if not raw_name: return "Unknown"
    # Убираем мусор из названия
    name = raw_name.replace(" на Arizona RP", "")
    name = name.replace(" — ARZ-WIKI", "")
    name = name.replace(" — Arizona RP Wiki", "")
    return name.strip()

def parse_vehicle_page(url):
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 1. ПАРСИНГ НАЗВАНИЯ (Усиленный) ---
        name = "Unknown"
        
        # Способ А: Ищем H1 (Заголовок статьи)
        h1_tag = soup.find('h1')
        if h1_tag:
            name = clean_text(h1_tag.text)
        
        # Способ Б: Если H1 пустой или Unknown, берем из <title>
        if name == "Unknown" or name == "":
            title_tag = soup.find('title')
            if title_tag:
                name = clean_text(title_tag.text)

        # Способ В: Мета-тег og:title
        if name == "Unknown" or name == "":
            meta_title = soup.find("meta", property="og:title")
            if meta_title:
                name = clean_text(meta_title["content"])

        # Чистим название от "на Arizona RP"
        name = fix_vehicle_name(name)

        # --- 2. ХАРАКТЕРИСТИКИ ---
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

        # --- 3. ОПИСАНИЕ ---
        content_div = soup.find('div', class_='entry-content')
        description_lines = []
        if content_div:
            for elem in content_div.find_all(['p', 'li']):
                # Игнорируем таблицы внутри текста
                if not elem.find_parent('table'):
                    text = clean_text(elem.text)
                    # Фильтруем совсем короткий мусор
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
    
    print("Начинаю парсинг машин...")

    while True:
        if page == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}page/{page}/"
            
        print(f"\n--- Страница {page} ---")
        
        try:
            response = scraper.get(url)
            
            if response.status_code == 404:
                print("Страницы закончились.")
                break
            
            if response.status_code != 200:
                print(f"Ошибка доступа: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все ссылки
            links = soup.find_all('a', href=True)
            vehicle_links = []
            
            for link in links:
                href = link['href']
                
                # ИСПРАВЛЕНИЕ ССЫЛКИ: Если ссылка относительная (/arz-rp/...), добавляем домен
                if href.startswith("/"):
                    href = BASE_DOMAIN + href
                
                # Фильтр ссылок: только машины
                if "/vehicles/" in href and href != BASE_URL and "/page/" not in href and "/category/" not in href:
                    if href not in vehicle_links:
                        vehicle_links.append(href)

            print(f"Найдено ссылок: {len(vehicle_links)}")
            
            if not vehicle_links:
                print("Машин нет. Возможно, конец.")
                break

            for v_url in vehicle_links:
                data = parse_vehicle_page(v_url)
                if data:
                    all_vehicles.append(data)
                time.sleep(0.3) # Небольшая пауза

            page += 1
            
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            break

    print(f"\nИТОГ: Сохранено {len(all_vehicles)} машин.")
    
    with open('vehicles.json', 'w', encoding='utf-8') as f:
        json.dump(all_vehicles, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    get_all_vehicles()
