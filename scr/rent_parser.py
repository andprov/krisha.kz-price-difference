import os
import re
import requests
import yaml
import csv

from bs4 import BeautifulSoup as bs
from tqdm import tqdm
from time import sleep
from datetime import date


def rental_data(
    city: int = 1,
    furniture: bool = True,
    room: int = 1,
    price_from: int = 100000,
    price_to: int = 300000,
    owner: bool = True,
) -> None:
    """
    Парсер объявлений аренды жилья.

    Note
    ____
    Варианты значения city:

    - 0 Весь Казахстан
    - 1 Алматы
    - 2 Астана
    - 3 Шымкент
    - 4 Абайская обл.
    - 5 Акмолинская обл.
    - 6 Актюбинская обл.
    - 7 Алматинская обл.
    - 8 Атырауская обл.
    - 9 Восточно-Казахстанская обл.
    - 10 Жамбылская обл.
    - 11 Жетысуская обл.
    - 12 Западно-Казахстанская обл.
    - 13 Карагандинская обл.
    - 14 Костанайская обл.
    - 15 Кызылординская обл.
    - 16 Мангистауская обл.
    - 17 Павлодарская обл.
    - 18 Северо-Казахстанская обл.
    - 19 Туркестанская обл.
    - 20 Улытауская обл.

    :param city: Город поиска. Доступен выбор от 0 до 20.
    :param furniture: Наличие мебели.
    :param room: Количество комнат. Доступен выбор от 0 до 4.
    :param price_from: Стоимость, нижний предел.
    :param price_to: Стоимость, верхний предел.
    :param owner: Объявление опубликовано собственником.

    """

    if city not in range(21):
        print("Параметр city должен быть в пределах от 0 до 20")
        exit()
    elif room not in range(5):
        print("Параметр room должен быть в пределах от 0 до 4")
        exit()

    check_site_status()
    search_result_first_page = first_page_url(
        city, furniture, room, price_from, price_to, owner
    )

    total_pages = get_total_pages(search_result_first_page)

    if total_pages:
        print(f"{total_pages[0]}.\nВсего страниц: {total_pages[1]}")
    else:
        print("Нет объявлений. Задайте другие параметры поиска.")
        exit()

    flats_data = get_flats(search_result_first_page, total_pages[1])

    print(create_csv(flats_data))


def check_site_status() -> None:
    try:
        req = requests.get("https://krisha.kz", timeout=5)
    except:
        print("Сайт недоступен.")
        exit()
    else:
        if req.status_code != 200:
            print("Ошибка, Код ответа:", req.status_code)
            exit()
        else:
            print("ОК. Код ответа:", req.status_code)


def first_page_url(
    city: int,
    furniture: bool,
    room: int,
    price_from: int,
    price_to: int,
    owner: bool,
) -> str:
    with open("scr/search_options.yaml") as file:
        search_options = yaml.safe_load(file)

    url = (
        f"https://krisha.kz/arenda/kvartiry/{search_options['cities'][city]}?"
        "das[_sys.hasphoto]=1"
        f"{search_options['furniture'][furniture]}"
        f"&das[live.rooms]={room}"
        f"&das[price][from]={price_from}"
        f"&das[price][to]={price_to}"
        f"{search_options['owner'][owner]}"
    )

    return url


def get_total_pages(page_url: str) -> tuple:
    page = requests.get(page_url)
    soup = bs(page.text, "html.parser")

    if soup.find("div", class_="a-search-options"):
        total_ads = soup.find("div", class_="a-search-subtitle").text.strip()

        if int("".join(re.findall(r"\d+", total_ads))) > 20:
            total_page = int(
                soup.find("nav", class_="paginator").text.split()[-2]
            )

            return total_ads, total_page
        else:
            return total_ads, 1


def get_flats(page_url: str, total_pages: int) -> list:
    home_page = "https://krisha.kz"
    flats_data = []

    for _ in tqdm(range(total_pages)):
        page = requests.get(page_url)
        soup = bs(page.text, "html.parser")
        flats = soup.find("section", class_="a-search-list").find_all(
            "div", attrs={"data-id": True}
        )

        for flat in flats:
            data_id = flat["data-id"]
            price = (
                flat.find("div", class_="a-card__price")
                .text.strip()
                .replace("\xa0", "")
                .replace("〒", "")
            )

            link = f"{home_page}/a/show/{data_id}"
            uuid = flat["data-uuid"]
            title = flat.find("a", class_="a-card__title").text.split(",")
            room = "".join(re.findall(r"\d+", title[0]))
            square = "".join(re.findall(r"\d+", title[1]))

            flat_data = {
                "id": data_id,
                "price": int(price),
                "link": link,
                "uuid": uuid,
                "room": room,
                "square": square,
            }

            flats_data.append(flat_data)

        sleep(0.5)

        if a := soup.find("a", class_="paginator__btn--next"):
            page_url = home_page + a.get("href").replace("%0A++++", "")

    return flats_data


def create_csv(data: list) -> str:
    if not os.path.isdir("data"):
        os.mkdir("data")

    now = date.today()
    path = f"data/{now}_flats.csv"
    columns = ["id", "price", "link", "uuid", "room", "square"]

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)

    return (
        f"Сохранено объявлений: {len(data)}\n"
        f"Файл с данными: {now}_flats.csv"
    )


if __name__ == "__main__":
    rental_data()
