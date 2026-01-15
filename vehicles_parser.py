import cloudscraper
from bs4 import BeautifulSoup
import json
import time
import re

# Настройки
BASE_DOMAIN = "https://arz-wiki.com"
BASE_URL = "https://arz-wiki.com/arz-rp/vehicles/"

# Меняем маскировку на Firefox (иногда помогает от Cloudflare на серверах)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'firefox',
        'platform': 'windows',
        'desktop': True
    }
)

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def fix_vehicle_name(raw_name):
    if not raw_name: return "Unknown"
    
    # 1. Убираем SEO-мусор ("🚗 Цены и скорость", "2026", "на Arizona RP")
    name = re.sub(r'🚗|Цены и скорость|202\d|на Arizona RP|— ARZ-WIKI', '', raw_name)
    
    # 2. Убираем ID в скобках, если он есть в названии (например "ЧубВоз (15765)")
    name = re.sub(r'\(\d+\)', '', name)
    
    # 3. Убираем лишние пробелы
    return clean_text(name)

def parse_vehicle_page(url):
    try:
        response = scraper.get(url)
        
        # Если защита вернула 403 или 503
        if response.status_code not in [200, 404]:
            print(f"[-] Блок Cloudflare ({response.status_code}): {url}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Проверка на капчу
        page_title = soup.title.text if soup.title else ""
        if "Just a moment" in page_title or "Attention Required" in page_title:
            print(f"[-] Поймали капчу на {url}. Пропуск.")
            return None

        # --- 1. НАЗВАНИЕ ---
        name = "Unknown"
        h1 = soup.find('h1', class_='entry-title')
        if h1:
            name = clean_text(h1.text)
        elif soup.title:
            name = clean_text(soup.title.text)
            
        name = fix_vehicle_name(name)

        if name in ["Транспорт", "Vehicles", "Unknown"]:
            return None

        # --- 2. ХАРАКТЕРИСТИКИ ---
        specs = {}
        rows = soup.find_all('tr')
        has_data = False # Флаг, нашли ли мы хоть что-то
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) == 2:
                key = clean_text(cols[0].text).replace(':', '')
                val = clean_text(cols[1].text)
                specs[key] = val
                has_data = True

        # !!! ВАЖНАЯ ПРОВЕРКА !!!
        # Если таблица пустая (has_data == False), значит страница битая или заблокирована.
        # Мы НЕ сохраняем такую машину.
        if not has_data:
            print(f"[-] Нет данных (пустая таблица): {name}")
            return None

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
                if not elem.find_parent('table'):
                    text = clean_text(elem.text)
                    if len(text) > 3 and "Cкорость" not in text:
                        description_lines.append(text)
        
        vehicle_data['description'] = "\n".join(description_lines)

        print(f"[+] Сохранено: {name}")
        return vehicle_data

    except Exception as e:
        print(f"[-] Ошибка: {e}")
        return None

def get_all_vehicles():
    all_vehicles = []
    page = 1
    
    print("=== ПАРСИНГ МАШИН (VER 3.0) ===")

    while True:
        if page == 1: url = BASE_URL
        else: url = f"{BASE_URL}page/{page}/"
            
        print(f"\n>>> Страница {page}...")
        
        try:
            response = scraper.get(url)
            if response.status_code != 200:
                print("Ошибка доступа или конец страниц.")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            vehicle_links = []
            
            for link in links:
                href = link['href']
                if href.startswith("/"): href = BASE_DOMAIN + href
                
                if "/vehicles/" in href and href != BASE_URL and "/page/" not in href and "/category/" not in href:
                    if href not in vehicle_links:
                        vehicle_links.append(href)

            print(f"Ссылок на странице: {len(vehicle_links)}")
            
            if not vehicle_links:
                print("Машин нет. Завершаем.")
                break

            for v_url in vehicle_links:
                data = parse_vehicle_page(v_url)
                if data:
                    all_vehicles.append(data)
                time.sleep(0.5) # Пауза важна

            page += 1
            
        except Exception as e:
            print(f"Ошибка цикла: {e}")
            break

    print(f"\nИТОГ: {len(all_vehicles)} машин.")
    
    # Сохраняем
    with open('vehicles.json', 'w', encoding='utf-8') as f:
        json.dump(all_vehicles, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    get_all_vehicles()
