from bs4 import BeautifulSoup
import requests
import re
from Apartment import Apartment
import json
import spacy

# real estate should delete itself based on expiry date
#
# update databases every day: if nothing new do nothing else add new entry(s)
# 	some form of index to check what exists in database
#
# check if there are more than 1 pages of ads and pull from those others
#
# consider using algolia search

url = 'http://gleanerclassifieds.com/showads/ad/search/section_id/10100/menu_id//category_id/12518/keyword//title' \
      '//start_rec/0/page_size/50/sort/3'

html_text = requests.get(url).text
soup = BeautifulSoup(html_text, 'lxml')
ads = soup.find_all('td')

rental_ads = []
count = 0
location_detected_count = 0
extracted_data = []


def extract_phone_number(text):
    phone_number = re.findall(r'\(?([0-9]{3})\)?([ .-]?)([0-9]{3})\2([0-9]{4})', text)
    if not phone_number:
        phone_number = re.findall(r'([0-9]{3})([ .-]?)([0-9]{4})', text)
    return phone_number


def extract_price(text):
    price = re.findall(r'\$ ?[ ,.]?[0-9,]{1,}[kK]?', text)
    return price


def extract_location(text):
    # using cliff recognition
    cliff_url = requests.get(f'http://localhost:8080/cliff-2.6.1/parse/text?q={text}')
    json_object = cliff_url.json()

    with open("./Regions.json") as f:
        regions = json.load(f)

    if json_object["status"] != "error":
        if json_object['results']['places']['mentions']:
            return json_object['results']['places']['mentions'][0]['source']['string'].upper()
        else:
            for region in regions["districts"]:
                if region.upper() in text.upper():
                    return region.upper()
                else:
                    for kingston in regions["kingstons"]:
                        if kingston.upper() in text.upper():
                            return kingston.upper()

    return []


for ad in ads:
    new_ad = ad.find('a')
    if new_ad is not None:
        if new_ad.text != "" and "Clear Search" not in new_ad.text:
            if "Banker" not in str(new_ad) and "Accomodation" not in str(new_ad):
                rental_ads.append(new_ad)
                links = re.findall(r'"(.*?)"', str(new_ad))
                if "thickbox" not in links[0]:
                    ad_page = requests.get(links[0]).text
                else:
                    ad_page = requests.get(links[1]).text
                ad_page_html = BeautifulSoup(ad_page, 'lxml')
                ad_page_html_rental_paragraph = ad_page_html.find_all('p')

                for rental_paragraph in ad_page_html_rental_paragraph:
                    paragraph = rental_paragraph.find_all("font")
                    if paragraph:
                        # print(f"Full Paragraph: {paragraph}")

                        if len(paragraph) <= 2:
                            index = 0
                            if not paragraph[0].text:
                                index = 1

                            if "img" not in str(paragraph[0]):
                                if paragraph[index].text and not \
                                        re.findall(r'([Mm][oO][vV][iI][nN][gG]|[Bb][oO][xX]|[Rr][eE][mM]'
                                                   r'[oO][vV][aA][lL]|[mM][oO][Vv][eE])', paragraph[index].text):
                                    # pull out data
                                    found_phone_number = extract_phone_number(paragraph[index].text)
                                    found_price = extract_price(paragraph[index].text)
                                    found_location = extract_location(paragraph[index].text)
                                    if found_location:
                                        print(f"Found Location: {found_location}\n")
                                        location_detected_count = location_detected_count + 1
                                    else:
                                        print(f"Full Ad: {paragraph[index].text}\n")
                                    data = Apartment(found_phone_number, found_price, paragraph[index].text)
                                    extracted_data.append(data)
                                    count = count + 1
                                    # print("Price", data.price)
                                    # print("\n")

print(f'Number of real estate option found: {count}')
print(f"Number of location detected from text: {location_detected_count}")
