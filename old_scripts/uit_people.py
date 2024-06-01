#!/usr/bin/env python3

import requests
import re

from sys import argv
from sys import exit

import bs4
from bs4 import BeautifulSoup

from rich import print as rprint
from rich.table import Table
from rich.columns import Columns

s: requests.Session = requests.Session()

s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.78 Safari/537.36"})
s.get("https://people.utah.edu/uWho/basic.hml")  # To get a needed cookie


def main_v1():
    url = 'https://people.utah.edu/uWho/basic.hml'
    # payload = {'searchTerm': 'Nathan Cable'} #DEBUG
    clear_two_lines_up = '\033[1A\033[2K\033[1A\033[2K'


    def search(url, query):
        r = s.post(url, data={'searchTerm': query, "_csrf": s.cookies.get("XSRF-TOKEN")})
        if r.status_code != 200:
            print(f'Error: The status code was {r.status_code} and not 200')
            exit(1)
        soup = BeautifulSoup(r.text, 'html.parser')
        # results = soup.findAll('a', href=re.compile('^basic.hml\?eid='))[0].get('href')
        results = soup.findAll('a', href=re.compile('^basic.hml\?eid='))
        if len(results) > 1:
            multiple_choice = input(f"There are {len(results)} search results, would you like to just view the first? (Y/N)\n>> ")
        else:
            # multiple_choice = 'y'
            result = results[0].get('href')
            search2(result)
            exit()
        if multiple_choice.lower() == 'n':
            number = input(f'{clear_two_lines_up}How many out of the total {len(results)} would you like to view?\n>> ')
            print(clear_two_lines_up, end='')
            if number.isdigit():
                number = int(number)
            else:
                print(f'Uh Oh, {number} is not a number! I\'ll just default the number of search results to 2')
                number = 2
            print('##################################################################')
            for index in range(number):
                result = results[index].get('href')
                # print(f'https://people.utah.edu/uWho/{result}')  # DEBUG
                search2(result)
                print('##################################################################')
            exit()
        elif multiple_choice.lower() == 'y':
            result = results[0].get('href')
            print(clear_two_lines_up, end='')
            search2(result)
            exit()


    def search2(result):
        url = f'https://people.utah.edu/uWho/{result}'
        r = s.get(url)
        if r.status_code != 200:
            print(f'Error: The status code was {r.status_code} and not 200')
            exit(2)
        else:
            soup = BeautifulSoup(r.text, 'html.parser')
            name = soup.find("span", text="Name").next_sibling
            name = name.strip()
            name_list = name.split(",")
            name = f'{name_list[1].strip()}, {name_list[0]}'
            name = f'{"Name:".ljust(15, ".")}{name}'
            title = info_grabber("Title", "span", soup)
            email = info_grabber("Email", "span", soup)
            dept = info_grabber("Dept/Org", "span", soup)
            phone = info_grabber("Phone", "span", soup)
            location = info_grabber("Location", "span", soup)
            address = info_grabber("Address", "span", soup)
            dept_id = info_grabber("Dept ID", "span", soup)
            print(f'{name}\n{title}\n{email}\n{dept}\n{phone}\n{location}\n{address}\n{dept_id}')


    def info_grabber(find, tag_type, the_soup):
        if find == "Email" or find == "Dept/Org":
            info = the_soup.find(tag_type, text=find).next_sibling.next_sibling.text
        elif find == "Address":
            name = f'{the_soup.find("span", text="Name").next_sibling.strip()}\r\n'
            info = the_soup.find(tag_type, text=find).next_sibling.next_sibling.text
            lines = info.replace(name, "").splitlines()
            info = []
            for line in lines:
                x = line.strip()
                if x == '':
                    pass
                else:
                    info.append(x)
            info = ", ".join(info)
        else:
            info = the_soup.find(tag_type, text=find).next_sibling
        info = info.strip()
        find = f'{find}:'.ljust(15, ".")
        info = f'{find}{info}'
        return info


    def terminal_to_script_variable_set(num: int = 1, prompt: str = "?> ", clear: bool = False) -> str:
        """
        Checks for # of argument passed to the script
        Input:
            num: the number of argument you want to search for
            prompt: What prompt to ask (remember to include a space)
            :bool clear: bool
        """
        arg_num = num + 1
        if len(argv) < arg_num:  # Argument number +1 because the first one is the script name
            arg = input(prompt)
            if clear:
                print('\033[1A\033[2K', end='')
        else:
            arg = argv[num]
        return arg


    arg1 = terminal_to_script_variable_set(1, "Who to look for?> ", True)
    # search(url, 'nathan')  # DEBUG
    search(url, arg1)


def search_for_results(search_term: str) -> str:  # TODO: add error and status code handling
    basic_search_url: str = "https://people.utah.edu/uWho/basic.hml"
    advanced_search_url: str = "https://people.utah.edu/uWho/advanced.hml"

    unid: bool = search_term.lower().startswith("u")

    basic_search_data: dict[str, str] = {
        "searchTerm": search_term,
        "_csrf": s.cookies.get("XSRF-TOKEN")
    }

    advanced_search_data: dict[str, str] = {
        "unid": search_term,
        "_csrf": s.cookies.get("XSRF-TOKEN")
    }

    search_results: requests.models.Response = s.post(
        url=advanced_search_url if unid else basic_search_url,
        data=advanced_search_data if unid else basic_search_data
    )
    return search_results.text


def parse_search_results_page(page: str):
    soup = BeautifulSoup(page, "html.parser")
    return soup.find_all("a", href=re.compile(r"\.hml\?eid="))


def get_people_page(href: str) -> str:  # TODO: add error and status code handling
    person_page: requests.models.Response = s.get(url=f"https://people.utah.edu/uWho/{href}")
    return person_page.text


def parse_person_page(page: str) -> dict[str, str]:
    soup = BeautifulSoup(page, "html.parser")
    u_who_details: list[bs4.element.Tag] = soup.select("div#uwhoDetails ol li")
    return {u_who_detail.span.text: " ".join(list(u_who_detail.stripped_strings)[1:]) for u_who_detail in u_who_details}


def table_generator(person_info: dict[str, str]) -> Table:
    table = Table(style="red", show_header=False, row_styles=("bold", "not bold"))
    table.add_column(justify="right")
    [table.add_row(*items) for items in person_info.items()]
    return table


def main_v2():
    """
    This function performs a search for results, parses the search results page,
    retrieves information from each person's page, generates a table for each person,
    and prints the results in a formatted column layout.
    """
    arg = argv[1]
    results_page = search_for_results(arg)
    people_list = parse_search_results_page(results_page)
    results: list[Table] = []
    for person in people_list:
        person_page = get_people_page(href=person.get("href"))
        person_info = parse_person_page(person_page)
        results.append(table_generator(person_info=person_info))
    rprint(Columns(results))


if __name__ == "__main__":
    try:
        main_v2()
    except KeyboardInterrupt:
        exit(130)

