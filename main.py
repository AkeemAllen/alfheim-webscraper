from bs4 import BeautifulSoup
import requests
import re
from python_graphql_client import GraphqlClient
from Apartment import Apartment
import json


# update databases every day: if nothing new do nothing else add new entry(s)
# 	some form of index to check what exists in database
#
# implement pagination in frontend
# consider using algolia search


def main():
    url = 'http://gleanerclassifieds.com/showads/ad/search/section_id/10100/menu_id//category_id/12518/keyword//title' \
          '//start_rec/0/page_size/50/sort/3'

    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'lxml')
    ads = soup.find_all('td')
    extracted_data = []
    full_set_of_ads = get_more_ads(soup, ads)

    print("Processing Advertisements...")
    for advertisement in full_set_of_ads[:150]:
        advertisement_content = advertisement.find('a')
        if advertisement_content is not None:
            if advertisement_content.text != "" and "Clear Search" not in advertisement_content.text:
                data = extract_relevant_data(advertisement_content)
                if data:
                    extracted_data.append(data[0])
                    # make_query(data[0])

    print("Completed Processing Advertisements")


def get_more_ads(first_soup, set_of_ads):
    more_ads = first_soup.find(id="page")
    navigations = more_ads.find_all("a", {"class": "pagingnav"})

    for nav in navigations:
        link = re.findall(r'http:\/\/[aA0-zZ9.\/]{1,}3', str(nav))
        new_page_html_text = requests.get(link[0]).text
        new_page_soup = BeautifulSoup(new_page_html_text, 'lxml')
        new_page_ads = new_page_soup.find_all('td')
        for advertisement in new_page_ads:
            set_of_ads.append(advertisement)

    return set_of_ads


def extract_phone_number(text):
    phone_number = re.findall(r'\(?([0-9]{3})\)?([ .-]?)([0-9]{3})\2([0-9]{4})', text)
    if not phone_number:
        phone_number = re.findall(r'([0-9]{3})([ .-]?)([0-9]{4,})', text)

    if phone_number[0][0] == "876":
        if len(phone_number[0]) < 4:
            contact = f'{phone_number[0][0]}-{phone_number[0][2]}'
        else:
            contact = f'{phone_number[0][0]}-{phone_number[0][2]}-{phone_number[0][3]}'
    else:
        contact = f'876-{phone_number[0][0]}-{phone_number[0][2]}'

    return contact


def extract_price(text):
    price = re.findall(r'\$ ?[ ,.]?[0-9,]{1,}[kK]?', text)

    if not price:
        price = re.findall(r'\$?[,.]?[0-9,]{1,}[kK]', text)

        if price:
            price[0] = '$' + price[0]

    if not price:
        return 'unspecified'

    try:
        if price[0][len(price[0]) - 1] == 'k' or price[0][len(price[0]) - 1] == 'K':
            price[0] = price[0][:-1] + ',000'
        elif price[0][len(price[0]) - 4] != ",":
            price[0] = price[0][:len(price[0]) - 3] + ',' + price[0][len(price[0]) - 3:]
    except IndexError:
        print(price)

    print(price)

    return price[0]


def extract_location(text):
    # using cliff recognition
    cliff_url = requests.get(f'http://localhost:8080/cliff-2.6.1/parse/text?q={text}')
    json_object = cliff_url.json()

    with open("./Regions.json") as f:
        regions = json.load(f)

    if json_object["status"] != "error":
        if json_object['results']['places']['mentions']:
            return json_object['results']['places']['mentions'][0]['source']['string'].capitalize()
        else:
            # Pulling out from own regions file
            for region in regions["districts"]:
                if region.upper() in text.upper():
                    return region.capitalize()
                else:
                    for kingston in regions["kingstons"]:
                        if kingston.upper() in text.upper():
                            return kingston.capitalize()

    return "Unspecified"


def extract_expiry_date(order_info):
    dates = order_info.find_all("td")
    return dates[3].text


def extract_relevant_data(advertisement_content):
    relevant_data = []
    if "Banker" not in str(advertisement_content) and "Accomodation" not in str(advertisement_content):
        links = re.findall(r'"(.*?)"', str(advertisement_content))
        if "thickbox" not in links[0]:
            ad_page = requests.get(links[0]).text
        else:
            ad_page = requests.get(links[1]).text
        ad_page_html = BeautifulSoup(ad_page, 'lxml')
        ad_page_html_rental_paragraph = ad_page_html.find_all('p')

        ad_page_order_info = ad_page_html.find(id="order-info")
        if ad_page_order_info is not None:
            found_expiry_date = extract_expiry_date(ad_page_order_info)

        for rental_paragraph in ad_page_html_rental_paragraph:
            paragraph = rental_paragraph.find_all("font")
            if paragraph:
                if len(paragraph) <= 2:
                    index = 0
                    if not paragraph[0].text:
                        index = 1
                    if "img" not in str(paragraph[0]):
                        if paragraph[index].text and not \
                                re.findall(r'([Mm][oO][vV][iI][nN][gG]|[Bb][oO][xX]|[Rr][eE][mM]'
                                           r'[oO][vV][aA][lL]|[mM][oO][Vv][eE])', paragraph[index].text):
                            found_phone_number = extract_phone_number(paragraph[index].text)
                            found_price = extract_price(paragraph[index].text)
                            found_location = extract_location(paragraph[index].text)
                            data = Apartment(found_phone_number, found_price,
                                             found_location, paragraph[index].text, found_expiry_date)
                            relevant_data.append(data)
    return relevant_data


def make_query(data):
    client = GraphqlClient("http://localhost:8081/graphql")

    query = '''
        mutation createRoom($location: String, $price: String, $contact: String
                                $description: String, $uuid: String, $expirationDate: String){
            createRoom(input: {
                location: $location,
                price: $price,
                uuid: $uuid,
                expirationDate: $expirationDate,
                description: $description
                contact: $contact
            }){
                id
                location
                expirationDate
                description
                image
                owner {
                    id
                }
                price
            }
        }
    '''

    variables = {
        "location": data.location,
        "price": data.price,
        "expirationDate": data.expiry_date,
        "uuid": "randomuuid",
        "description": data.desc,
        "contact": data.phone_number
    }

    result = client.execute(query=query, variables=variables)
    print(result)


if __name__ == "__main__":
    main()
