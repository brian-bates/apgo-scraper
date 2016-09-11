"""Scraps apgo.org for OB/GYN residency program information

Generates a CSV file of a bunch of info on OB/GYN residency programs in the US
and Canada by scraping the apgo.org website."""

from __future__ import print_function
import collections
import csv
import httplib
import requests

ResidencyInfo = collections.namedtuple(
    'ResidencyInfo', ['name',
                      'state',
                      'city',
                      'salary',
                      'pto',
                      'min_step_scores',
                      'avg_step_scores',
                      'resident_demographics',
                      'last_updated'])


ResidentDemographics = collections.namedtuple(
    'ResidentDemographics', ['total', 'male', 'female'])


class AuthError(Exception):
    pass


class ScrapingError(Exception):
    pass


def scrape_page(id_):
    """Scrape a single page of the residency directory.

    Returns the page text. Throws an AuthError if the page says we are not
    authorized (usually means there isn't an entry).Throws a ScrapingError if
    we it is possibly a legit entry, but we can't scrap it (usually a
    connection error caused by performance issues with apgo.org).

    Args:
        id_ (int): id number of the directory entry to scrape

    Throws:
        ScrapingError
    """
    url = 'https://www.apgo.org/component/residencydirectory/id/{}'.format(id_)
    try:
        resp = requests.get(url, timeout=30)
    except requests.ConnectionError:
        raise ScrapingError('ConnectionError')
    if resp.status_code != httplib.OK:
        raise ScrapingError(
            'Failed to get page. Status code {}'.format(resp.status_code))
    # The website does not use proper http codes so we have to scan the
    # content to check for auth errors.
    if 'Not Authorized' in resp.text:
        raise AuthError()
    return resp.text


def safe_scrape_item_between(source, before, after, instance=1):
    """Return the substring between before and after else an empty string

    Args:
        source (str): String to search.
        before (str): String right before what we are searching for.
        after (str): String right after what we are searching for)

    Kwargs:
        instance (int): Return the 'instance'th entry found. Defaults to 1.
    """
    text = ''
    try:
        text = scrape_item_between(source, before, after, instance=instance)
    except ScrapingError:
        pass
    return text


def scrape_item_between(source, before, after, instance=1):
    """Return the substring between before and after

    Throws an ScrapingError error if no such item exists.

    Args:
        source (str): String to search.
        before (str): String right before what we are searching for.
        after (str): String right after what we are searching for)

    Kwargs:
        instance (int): Return the 'instance'th entry found. Defaults to 1.
    """
    try:
        text = source.split(before)[instance].split(after)[0]
    except IndexError:
        raise ScrapingError(
            'Failed to scrape item between "{}" and "{}"'.format(before,
                                                                 after))
    return text


def scrape_section(source, section_number):
    """Target a specific section number"""
    before = '{}.&nbsp;'.format(section_number)
    after = '{}.&nbsp;'.format(section_number + 1)
    return scrape_item_between(source, before, after)


def scrape_name(source):
    """Scrape the program name"""
    before = 'Program Name:&nbsp;<span class="bold">'
    after = '</span>'
    return safe_scrape_item_between(source, before, after)


def scrape_state(source):
    """Scrape the state (or providence) that the program is in"""
    before = '&nbsp;State/Providence:&nbsp;<span class="bold">'
    after = '</span>'
    return safe_scrape_item_between(source, before, after)


def scrape_city(source):
    """Scrape the city that the program is in"""
    before = 'City:&nbsp;<span class="bold">'
    after = '</span>'
    return safe_scrape_item_between(source, before, after)


def scrape_salary(source):
    """Scrapes the source for a list of salaries by year"""
    # Salary is contained in section 10
    section = scrape_section(source, 10)
    before = '<span class="bold">'
    after = '</span>'
    return [safe_scrape_item_between(section, before, after),
            safe_scrape_item_between(section, before, after, instance=3),
            safe_scrape_item_between(section, before, after, instance=5),
            safe_scrape_item_between(section, before, after, instance=7)]


def scrape_pto(source):
    """Scrapes the source for a list of payed time off (pto) by year"""
    # PTO is contained in section 10
    section = scrape_section(source, 10)
    before = '<span class="bold">'
    after = '</span>'
    return [safe_scrape_item_between(section, before, after, instance=2),
            safe_scrape_item_between(section, before, after, instance=4),
            safe_scrape_item_between(section, before, after, instance=6),
            safe_scrape_item_between(section, before, after, instance=8)]


def scrape_avg_step_score(source):
    """Scrapes the source for a list of average step 1 and 2 scores"""
    # 19 = avg step scores section
    section = scrape_section(source, 19)
    before = '<span class="bold">'
    after = '</span>'
    return [safe_scrape_item_between(section, before, after, instance=1),
            safe_scrape_item_between(section, before, after, instance=2)]


def scrape_min_step_score(source):
    """Scrapes the source for a list of min step 1 and 2 scores"""
    # 27 = min step scores section
    section = scrape_section(source, 27)
    before = '<span class="bold">'
    after = '</span>'
    return [safe_scrape_item_between(section, before, after, instance=2),
            safe_scrape_item_between(section, before, after, instance=3)]


def scrape_resident_demographics(source):
    """Scrapes the source for demographics of accepted residents"""
    # 17 = resident demographics
    section = scrape_section(source, 17)
    before = '<span class="bold">'
    after = '</span>'
    total = safe_scrape_item_between(section, before, after, instance=1)
    female = safe_scrape_item_between(section, before, after, instance=3)
    male = safe_scrape_item_between(section, before, after, instance=4)
    return ResidentDemographics(total=total, female=female, male=male)


def scrape_last_updated(source):
    """Scraptes the source for when the data was last updated"""
    before = 'Last Updated: <span class="bold">'
    after = '<'
    return safe_scrape_item_between(source, before, after)


def get_residency_info(id_):
    """Scrapes the info from a residency program with the given id"""
    page_source = scrape_page(id_)
    return ResidencyInfo(
        name=scrape_name(page_source),
        state=scrape_state(page_source),
        city=scrape_city(page_source),
        salary=scrape_salary(page_source),
        pto=scrape_pto(page_source),
        min_step_scores=scrape_min_step_score(page_source),
        avg_step_scores=scrape_avg_step_score(page_source),
        resident_demographics=scrape_resident_demographics(page_source),
        last_updated=scrape_last_updated(page_source))


def scrape():
    """Scrapes the residency directory of the apgo.org website

    Returns a list of residency programs and their infomation
    """
    print('Starting Scraper...')
    all_residency_info = []
    LAST_ID = 287
    for id_ in range(1, LAST_ID):
        print('Scraping id {}...\t'.format(id_), end="")
        try:
            residency_info = get_residency_info(id_)
            all_residency_info.append(residency_info)
            print('SUCCESS')
        except (AuthError, requests.exceptions.ReadTimeout):
            print('SKIP')
        except ScrapingError:
            print('FAIL')
    print('Done.')
    return all_residency_info


def generate_csv(residency_programs):
    """Writes a CSV file of residency program info to the current directory"""
    print('Generating CSV...')
    headers = ['Name',
               'State',
               'City',
               'Salary PG1',
               'Salary PG2',
               'Salary PG3',
               'Salary PG4',
               'PTO PG1',
               'PTO PG2',
               'PTO PG3',
               'PTO PG4',
               'Min Step 1 Score',
               'Min Step 2 Score',
               'Avg. Step 1 Score',
               'Avg. Step 2 Score',
               'Residents (Total)',
               'Residents (Male)',
               'Residents (Female)',
               'Last Updated']
    with open('residency_info.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for residency_info in residency_programs:
            row = [residency_info.name,
                   residency_info.state,
                   residency_info.city,
                   residency_info.salary[0],
                   residency_info.salary[1],
                   residency_info.salary[2],
                   residency_info.salary[3],
                   residency_info.pto[0],
                   residency_info.pto[1],
                   residency_info.pto[2],
                   residency_info.pto[3],
                   residency_info.min_step_scores[0],
                   residency_info.min_step_scores[1],
                   residency_info.avg_step_scores[0],
                   residency_info.avg_step_scores[1],
                   residency_info.resident_demographics.total,
                   residency_info.resident_demographics.male,
                   residency_info.resident_demographics.female,
                   residency_info.last_updated]
            writer.writerow([unicode(s).encode("utf-8") for s in row])
    print('Done.')


def main():
    residency_programs = scrape()
    generate_csv(residency_programs)

if __name__ == '__main__':
    main()
