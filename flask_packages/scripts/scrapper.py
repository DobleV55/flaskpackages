import os
import datetime
import urllib.parse

import requests

from bs4 import BeautifulSoup
from pymongo import MongoClient


def db_connection():

    flask_packages_enviro = os.environ['FLASK_PACKAGES_ENVIRO']
    split = flask_packages_enviro.split(',')
    db_password = split[0]
    db_connection = split[1]
    cluster = MongoClient("mongodb+srv://user:"+db_password+"@"+db_connection+"/test?retryWrites=true&w=majority")
    db = cluster['flask_db']
    collection = db['flask_packages']

    search_packages(collection)


def search_packages(collection):

    count = 0  # Counter for search pages in pypy.org
    while count < 42:
        count = count+1
        url = 'https://pypi.org/search/?c=Framework+%3A%3A+Flask&o=&q=&page='+str(count)

        r = requests.get(url)

        soup = BeautifulSoup(r.content, 'html.parser')

        all_packages = soup.find_all('h3', {'class': 'package-snippet__title'})

        for pypi_package_info in all_packages:
            name = pypi_package_info.find('span', {'class': 'package-snippet__name'}).text

            find_on_db = list(collection.find({"name": name}))

            print(name)
            if find_on_db == []:
                last_db_version = None
                package_info = collect_info(pypi_package_info, name, collection, last_db_version)
                add_package_to_db(package_info, collection)
            else:
                last_db_version = compare_versions(pypi_package_info, name, collection)
                if last_db_version is not None:
                    package_info = collect_info(pypi_package_info, name, collection, last_db_version)
                    update_package_on_db(package_info, collection, last_db_version)
                else:
                    continue

def compare_versions(pypi_package_info, name, collection):

    package_last_version = pypi_package_info.find('span', {'class': 'package-snippet__version'}).text
    db_search_package = collection.find({"name": name})
    for objects in db_search_package:
        last_db_version = (objects["lastest_version"])
    if package_last_version == last_db_version:
        return None
    else:
        return last_db_version


def collect_info(pypi_package_info, name, collection, last_db_version):

    project_url = 'https://pypi.org/project/'
    project_url = urllib.parse.urljoin(project_url, name)
    response = requests.get(project_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # DESCRIPTION
    find_description = soup.find_all('div', {'class': 'project-description'})
    if find_description == []:
        description = ""
    else:
        description = str(find_description[0])

    # LASTEST VERSION

    lastest_version = pypi_package_info.find('span', {'class': 'package-snippet__version'}).text

    # ALL VERSIONS + SHA256 + DATE PER VERSION + LINK PER VERSION

    url = 'https://pypi.org/project/'
    add = '/#history'
    project_url_versions = urllib.parse.urljoin(url, name, add)

    response = requests.get(project_url_versions)

    soup_versions = BeautifulSoup(response.text, 'lxml')
    versions_number = soup_versions.findAll('a', {'class': ['card', 'release__card']})

    all_versions = []
    for version in versions_number:
        try:
            version_number = version.find('p', {'class': 'release__version'}).text.strip()
            if last_db_version is not None:
                if version_number == last_db_version:
                    break
            date_box = version.find('p', {'class': 'release__version-date'})
            date = date_box.find('time')['datetime']
            url = 'https://pypi.org/project/'+name+'/'+version_number+'/#files'
            response = requests.get(url)
            soup_version = BeautifulSoup(response.text, 'lxml')
            link_block = soup_version.find('th', {'scope': 'row'})
            link = link_block.find('a')['href']

            try:
                link = link_block.find('a')['href']
                sha256 = soup.find('code').text
            except:
                version_number = (version_number.splitlines()[0])
                url = 'https://pypi.org/project/'+name+'/'+version_number+'/#files'
                response = requests.get(url)
                soup_version = BeautifulSoup(response.text, 'lxml')
                link_block = soup_version.find('th', {'scope': 'row'})
                link = link_block.find('a')['href']
                sha256 = soup_version.find('code').text
            all_versions.append({
                                'version': version_number,
                                'date': date,
                                'link': link,
                                'sha256': sha256
                                })
        except:
            continue

        all_versions.append({
                            'version': version_number,
                            'date': date,
                            'link': link,
                            'sha256': sha256
                            })

    # MAINTAINER
    maintainer_find = soup.find('span', {'class': 'sidebar-section__user-gravatar-text'})
    maintainer = maintainer_find.text.strip()

    # HOMEPAGE

    homepage_info = soup.find('a', {'class': 'vertical-tabs__tab vertical-tabs__tab--with-icon vertical-tabs__tab--condensed'})
    homepage_link = homepage_info["href"]

    # CLASSIFIERS

    classifiers_div = soup.find('ul', {'class': 'sidebar-section__classifiers'})

    lis = classifiers_div.find_all('li')
    classifiers = {}
    for item in lis:
        if item.find('strong'):
            title = item.find('strong').text
            tag = item.find('a')
            tag = tag.text.strip()
            title = title.lower()
            title = title.replace(' ', '_')
            classifiers[title] = str(tag)

    # PYPI LINK

    pypi_url = 'https://pypi.org/project/'
    project_url = urllib.parse.urljoin(pypi_url, name)

    # RELEASED

    find_released_date = pypi_package_info.find('span', {'class': 'package-snippet__released'}).text.strip()
    released_date = datetime.datetime.strptime(find_released_date, '%b %d, %Y')
    released_date = released_date.date()
    released_date = str(released_date)

    # LICENSE

    project_license = []
    meta_div = soup.find_all('div', {'class': 'sidebar-section'})
    for div in meta_div:
        for item in div:
            try:
                if item.text == 'Meta':
                    lice = div.find('p').text
                    lice = lice.split(':')
                    project_license.append(lice[-1])

            except:
                pass
    project_license = list(set(project_license))
    project_license = str(project_license[0])

    package_info = {
        "name": name,
        "description": description,
        "lastest_version": lastest_version,
        "versions": all_versions,
        "maintainer": maintainer,
        "homepage": homepage_link,
        "classifiers": classifiers,
        "pypi_link": project_url,
        "released": released_date,
        "license": project_license
    }
    return package_info

def add_package_to_db(package_info, collection):

    ENDC = '\033[m'
    TYELLOW = '\033[93m'
    print(TYELLOW + "agregando: ", package_info['name'], ENDC)
    collection.insert_one(package_info)


def update_package_on_db(package_info, collection, last_db_version):
    print('ahora?')
    print(package_info['name'])
    ENDC = '\033[m'
    TGREEN = '\033[32m'
    print(TGREEN + "actualizando", package_info['name'], ENDC)
    print('db version: ', last_db_version)
    print('new version: ', package_info["lastest_version"])

    old_package = collection.find_one({"name": package_info['name']})

    old_package["description"] = package_info["description"]
    old_package["lastest_version"] = package_info["lastest_version"]
    old_package['versions'] = package_info["versions"]
    old_package["maintainer"] = package_info["maintainer"]
    old_package["homepage"] = package_info["homepage"]
    old_package['classifiers'] = package_info["classifiers"]
    old_package['pypi_link'] = package_info["pypi_link"]
    old_package['released'] = package_info["released"]
    old_package['license'] = package_info["license"]

    old_package.pop('_id')

    collection.update_one({"name": package_info['name']}, {'$set': old_package})


if __name__ == "__main__":
    db_connection()
