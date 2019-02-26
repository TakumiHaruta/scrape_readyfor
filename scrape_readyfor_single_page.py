import requests
import time
import lxml.html
import re
import os
import csv
import traceback
import sys
import codecs

from datetime import date
from shutil import copyfile


exec_date = str(date.today())

def main(url):
    print("Start!!")

    # プロジェクトページから欲しいデータを保存
    print('Crawling project pages')
    id = 1
    res = requests.get(url)
    scrape_project_info(res.text, url, id)


def scrape_project_info(text, project_url, id):
    """
    プロジェクトページをスクレイプし、csvに書き込む
    """
    html = lxml.html.fromstring(text)

    # 属性データ
    project_name = html.xpath('//h1/a')[0].text
    tags = [tag.text for tag in html.xpath('//ul[@class="tags"]//a')]
    project_type = html.xpath('//div[@class="project-attributes-badge"]/div')[0].text
    funding_model = html.xpath('//div[@class="project-attributes-badge"]/div')[1].text
    try:
        funding_goal = html.xpath('//div[@class="Project-visual__conditions"]//*[text()="目標金額"]/parent::node()/following-sibling::dd')[0].text
    except IndexError:
        funding_goal = None
    return_price = html.xpath('//span[@class="Project-return__price"]')
    return_prices = [price.text for price in return_price]

    # 時系列データ
    total_fund = html.xpath('//div[@class="Project-visual__conditions"]//dd')[0].text
    try:
        backers = html.xpath('//div[@class="Project-visual__conditions"]//*[text()="支援者数" or text()="寄附者数"]/following-sibling::dd')[0].text
    except IndexError:
        backers = None
    try:
        days_to_go = html.xpath('//div[@class="Project-visual__conditions"]//*[text()="残り日数"]/following-sibling::dd/span')[0].text
    except IndexError:
       days_to_go = None
    try:
        percent_funded = html.xpath('//div[@class="Gauge__txt"]')[0].text
    except IndexError:
        percent_funded = html.xpath('//div[contains(@class, "Project-visual__alert") and contains(@class, "is-complete")]/span')[0].text
    new_info = html.xpath('//div[@class="tab-wrapper"]//span[text()="新着情報"]/following-sibling::span')[0].text
    comments = html.xpath('//div[@class="tab-wrapper"]//span[text()="応援コメント"]/following-sibling::span')[0].text
    favo_users = re.search(r'"watchlists_count":([0-9]+),', text).group(1)
    img_tags = len(re.findall(r'<img .*?>', text))

    cnt_words_list = html.xpath('//section[contains(@class, "Project-outline") and contains(@class, "Tab__content")]//text()')
    cnt_words = len(''.join(cnt_words_list).replace('\r', '').replace('\n', ''))

    project_info_data = [
        id,
        exec_date,
        project_url,
        project_name,
        tags,
        project_type,
        funding_model,
        funding_goal,
        return_prices,
        total_fund,
        backers,
        days_to_go,
        percent_funded,
        new_info,
        comments,
        favo_users,
        img_tags,
        cnt_words,
    ]

    # 仮にcsvでデータ保存


    print(project_info_data)


if __name__ == '__main__':
    url = sys.argv[1]
    main(url)
