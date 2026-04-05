import requests
import time
from terminaltables import AsciiTable
from dotenv import load_dotenv
import os


load_dotenv()

HH_URL = "https://api.hh.ru/vacancies"
SUPERJOB_API_URL = "https://api.superjob.ru/2.0/vacancies/"
SUPERJOB_API_KEY = os.environ["SUPERJOB_API_KEY"]

MOSCOW_HH_AREA = 1
MOSCOW_SJ_TOWN = 4

# (отображаемое имя, поисковый запрос)
LANGUAGES = [
    ("python", "python"),
    ("c", "c"),
    ("c#", "c#"),
    ("c++", "c++"),
    ("java", "java"),
    ("js", "javascript"),
    ("ruby", "ruby"),
    ("go", "go"),
    ("1c", "1c"),
]


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    if salary_from:
        return float(salary_from)
    if salary_to:
        return float(salary_to)
    return None


def predict_rub_salary_hh(vacancy):
    salary = vacancy.get("salary")
    if not salary:
        return None

    if salary.get("currency") != "RUR":
        return None

    return predict_salary(
        salary.get("from"),
        salary.get("to"),
    )


def predict_rub_salary_for_superJob(vacancy):
    if vacancy.get("currency") not in ("rub", "RUB", 0, 1):
        return None

    salary_from = vacancy.get("payment_from")
    salary_to = vacancy.get("payment_to")

    if salary_from == 0:
        salary_from = None
    if salary_to == 0:
        salary_to = None

    return predict_salary(salary_from, salary_to)


def get_hh_statistics(search_query):
    page = 0
    per_page = 100
    salaries = []
    vacancies_found = 0

    while True:
        params = {
            "text": search_query,
            "area": MOSCOW_HH_AREA,
            "page": page,
            "per_page": per_page,
        }

        response = requests.get(HH_URL, params=params)
        response.raise_for_status()
        data = response.json()

        vacancies_found = data["found"]

        for vacancy in data["items"]:
            salary = predict_rub_salary_hh(vacancy)
            if salary is not None:
                salaries.append(salary)

        page += 1
        if page >= data["pages"]:
            break

        time.sleep(0.2)

    vacancies_processed = len(salaries)
    average_salary = int(sum(salaries) / vacancies_processed) if salaries else 0

    return {
        "vacancies_found": vacancies_found,
        "vacancies_processed": vacancies_processed,
        "average_salary": average_salary,
    }


def get_superjob_statistics(search_query):
    headers = {
        "X-Api-App-Id": SUPERJOB_API_KEY
    }

    page = 0
    count = 100
    salaries = []
    vacancies_found = 0

    while True:
        params = {
            "keyword": search_query,
            "town": MOSCOW_SJ_TOWN,
            "page": page,
            "count": count,
        }

        response = requests.get(
            SUPERJOB_API_URL,
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        data = response.json()

        vacancies_found = data["total"]

        for vacancy in data["objects"]:
            salary = predict_rub_salary_for_superJob(vacancy)
            if salary is not None:
                salaries.append(salary)

        if not data["more"]:
            break

        page += 1
        time.sleep(0.2)

    vacancies_processed = len(salaries)
    average_salary = int(sum(salaries) / vacancies_processed) if salaries else 0

    return {
        "vacancies_found": vacancies_found,
        "vacancies_processed": vacancies_processed,
        "average_salary": average_salary,
    }


def get_statistics(get_stats_func):
    statistics = {}

    for lang_name, query in LANGUAGES:
        print(f"Собираю данные для {lang_name}...")
        statistics[lang_name] = get_stats_func(query)

    return statistics


def print_statistics(statistics, title):
    table_data = [
        [
            "Язык программирования",
            "Найдено вакансий",
            "Обработано вакансий",
            "Средняя зарплата",
        ]
    ]

    for language, stats in statistics.items():
        table_data.append([
            language,
            stats["vacancies_found"],
            stats["vacancies_processed"],
            stats["average_salary"],
        ])

    table = AsciiTable(table_data, title)
    print(table.table)


def main():
    hh_stats = get_statistics(get_hh_statistics)
    sj_stats = get_statistics(get_superjob_statistics)

    print_statistics(hh_stats, "HeadHunter Moscow")
    print()
    print_statistics(sj_stats, "SuperJob Moscow")


if __name__ == "__main__":
    main()