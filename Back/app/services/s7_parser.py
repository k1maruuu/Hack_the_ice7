# app/services/s7_parser.py

import datetime as dt
import time
import re
from pathlib import Path
from typing import Optional, List, Dict


from playwright.sync_api import sync_playwright

# ---------- мини-словарь город → IATA ----------
CITY_IATA = {
    "москва": "MOW", "санкт-петербург": "LED", "новосибирск": "OVB",
    "екатеринбург": "SVX", "казань": "KZN", "сочи": "AER",
    "владивосток": "VVO", "краснодар": "KRR", "самара": "KUF",
    "уфа": "UFA", "красноярск": "KJA", "омск": "OMS",
    "челябинск": "CEK", "иркутск": "IKT", "нижний новгород": "GOJ",
    "пермь": "PEE", "ростов": "ROV", "волгоград": "VOG",
    "астрахань": "ASF", "мурманск": "MMK", "петропавловск-камчатский": "PKC",
    "якутск": "YKS",
}
# -----------------------------------------------


def city_to_iata(city: str) -> str:
    """
    Возвращает IATA-код по-русски или уже готовому коду.
    Если не нашли в словаре, считаем, что это уже IATA (3 лат. буквы)
    и просто возвращаем upper().
    """
    c = city.strip().lower()
    if c in CITY_IATA:
        return CITY_IATA[c]
    if len(c) == 3 and c.isalpha():
        return c.upper()
    # backend-версия: не спрашиваем пользователя, просто вернём как есть
    return city.upper()


def parse_ibe_page(page) -> List[Dict]:
    """
    Парсит рейсы со страницы выбора перелёта S7.
    Основа взята из исходного parser_s7_working.py.
    """
    try:
        page.wait_for_selector("[data-qa='tripItem']", timeout=60_000)
        page.wait_for_timeout(3_000)
    except Exception:
        # можно логировать, кидать исключение и т.п.
        return []

    cards = page.locator("[data-qa='tripItem']").all()
    if not cards:
        return []

    flights: list[dict] = []

    for i, card in enumerate(cards, start=1):
        try:
            direction = card.get_attribute("data-direction") or ""

            carrier = ""
            try:
                carrier = (
                    card.locator("[class*='title_logo']")
                    .first.inner_text(timeout=1_000)
                    .strip()
                )
            except Exception:
                pass

            if direction:
                flight_no = f"{carrier} {direction}".strip()
            else:
                flight_no = f"{carrier or 'S7'} #{i}"

            dep_time = ""
            arr_time = ""
            try:
                time_nodes = card.locator("[class*='segment_route__time']").all()
                if len(time_nodes) >= 2:
                    dep_time = time_nodes[0].inner_text().strip()
                    arr_time = time_nodes[-1].inner_text().strip()
            except Exception:
                pass

            price_rub = 0
            try:
                price_nodes = card.locator("[data-qa='cost_tariffItem']").all()
                prices = []
                for node in price_nodes:
                    txt = node.inner_text().strip()
                    digits = "".join(ch for ch in txt if ch.isdigit())
                    if digits:
                        prices.append(int(digits))
                if prices:
                    price_rub = min(prices)
            except Exception:
                pass

            flights.append(
                {
                    "flight_no": flight_no,
                    "dep_time": dep_time,
                    "arr_time": arr_time,
                    "price_rub": price_rub,
                }
            )
        except Exception:
            continue

    return flights


def fill_search_form(page, origin: str, dest: str, date_out: str, date_back: Optional[str]):
    """
    Заполняет форму поиска на странице S7.
    Взято из исходного кода, убраны print/input.
    """
    page.wait_for_timeout(2000)

    def input_near_text(text: str):
        label = page.get_by_text(text, exact=True).first
        for up in range(1, 6):
            container = label.locator("xpath=" + "/.." * up)
            inputs = container.locator("input:not([type='hidden'])")
            if inputs.count() > 0:
                return inputs.nth(0)
        raise RuntimeError(f"Не нашёл видимый input рядом с текстом «{text}»")

    def click_suggestion_below_field(field_locator):
        box = field_locator.bounding_box()
        if not box:
            return
        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] + 35
        page.mouse.click(x, y)

    def open_calendar_for_label(label_text: str):
        page.wait_for_timeout(500)
        label = page.get_by_text(label_text, exact=True).first
        box = label.bounding_box()
        x = box["x"] + box["width"] - 20
        y = box["y"] + box["height"] / 2
        page.mouse.click(x, y)

    def pick_date_for_label(label_text: str, date_str: str):
        target = dt.datetime.strptime(date_str, "%d.%m.%Y")

        month_stems = {
            1: "январ",  2: "феврал", 3: "март",
            4: "апрел", 5: "ма",     6: "июн",
            7: "июл",   8: "август", 9: "сентябр",
            10: "октябр", 11: "ноябр", 12: "декабр",
        }
        mstem = month_stems[target.month]

        open_calendar_for_label(label_text)

        header_pattern = re.compile(f"{mstem}.*{target.year}", re.I)

        for _ in range(24):
            try:
                header = page.get_by_text(header_pattern).first
                if header.is_visible():
                    break
            except Exception:
                pass
            try:
                next_btn = page.get_by_role("button", name=re.compile("следующий", re.I)).first
                if next_btn.is_visible():
                    next_btn.click()
                    page.wait_for_timeout(1000)
                    continue
            except Exception:
                break

        day_pattern = re.compile(rf"\b{target.day}\b.*{mstem}.*{target.year}", re.I)
        try:
            btn = page.get_by_role("button", name=day_pattern).first
            if btn.is_visible():
                btn.click()
                return
        except Exception:
            pass

        try:
            calendar = page.locator(
                "xpath=//div[contains(@class,'calendar') or contains(@class,'datepicker')]"
            ).first
            day_loc = calendar.locator(f"xpath=.//*[text()='{target.day}']").first
            if day_loc.is_visible():
                day_loc.click(force=True)
                return
        except Exception:
            pass

        try:
            page.get_by_text(str(target.day), exact=True).first.click(force=True)
        except Exception:
            pass

    # Тип поездки
    if date_back:
        try:
            rt_radio = page.get_by_role("radio", name=re.compile("Туда и обратно", re.I))
            rt_radio.click()
        except Exception:
            pass
    else:
        try:
            ow_radio = page.get_by_role("radio", name=re.compile("В одну сторону", re.I))
            ow_radio.click()
        except Exception:
            pass

    page.wait_for_timeout(1000)

    # Откуда
    origin_field = input_near_text("Откуда")
    origin_field.click()
    origin_field.fill("")
    origin_field.type(origin, delay=80)
    page.wait_for_timeout(1000)
    click_suggestion_below_field(origin_field)

    page.wait_for_timeout(1000)

    # Куда
    dest_field = input_near_text("Куда")
    dest_field.click()
    dest_field.fill("")
    dest_field.type(dest, delay=80)
    page.wait_for_timeout(1000)
    click_suggestion_below_field(dest_field)

    page.wait_for_timeout(1000)

    # Дата туда
    pick_date_for_label("Туда", date_out)
    page.wait_for_timeout(1000)

    # Дата обратно (если есть)
    if date_back:
        try:
            rt_radio = page.get_by_role("radio", name=re.compile("Туда и обратно", re.I))
            rt_radio.click()
        except Exception:
            pass
        pick_date_for_label("Обратно", date_back)

    page.wait_for_timeout(1000)

    # Кнопка поиска
    try:
        search_button = None
        for text in ["Искать", "Найти рейсы", "Найти билеты", "Найти"]:
            try:
                search_button = page.get_by_role("button", name=re.compile(text, re.I))
                if search_button.is_visible():
                    break
            except Exception:
                search_button = None

        if search_button is None:
            search_button = page.get_by_text(re.compile("Искать|Найти", re.I)).first

        if search_button is None:
            raise RuntimeError("Кнопка поиска не найдена")

        search_button.click()
    except Exception:
        pass


def run_s7_search(
    origin: str,
    dest: str,
    date_out: str,
    date_back: Optional[str] = None,
) -> List[Dict]:
    """
    Верхнеуровневая функция для использования в FastAPI router’е.
    Принимает строки (города/коды и даты ДД.ММ.ГГГГ) и возвращает список рейсов.
    """
    origin_iata = city_to_iata(origin)
    dest_iata = city_to_iata(dest)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # в бекенде headless=True
        page = browser.new_page()
        page.set_default_timeout(60_000)

        start_url = "https://ibe.s7.ru/air"
        page.goto(start_url, wait_until="domcontentloaded")
        page.wait_for_url("**/air?execution=*", timeout=60_000)

        fill_search_form(page, origin_iata, dest_iata, date_out, date_back)

        time.sleep(5)  # чуть ждём загрузки результатов
        flights = parse_ibe_page(page)

        browser.close()

    return flights

# print(run_s7_search("vvo", "yks", "25.11.2025", ""))