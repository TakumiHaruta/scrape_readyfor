import requests
import time
import lxml.html
import re
import os
import csv
import traceback
import sys
import codecs

from slackclient import SlackClient
from datetime import date
from shutil import copyfile


SLACK_TOKEN = os.getenv('SLACK_TOKEN')
FB_API_TOKEN = os.getenv('FB_API_TOKEN')

sc = SlackClient(SLACK_TOKEN)

proxies = {
    'http': 'http://proxy_host:8080',
    'https': 'http://proxy_host:8080',
}

exec_date = str(date.today())
root_path = 'data/{}'.format(exec_date)
os.makedirs('{}/html'.format(root_path), exist_ok=True)

with codecs.open('{}/crowdfunding_data.csv'.format(root_path), 'w', 'utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        'id',
        'exec_date',
        'project_url',
        'project_name',
        'tags',
        'project_type',
        'funding_model',
        'funding_goal',
        'return_prices',
        'total_fund',
        'backers',
        'days_to_go',
        'percent_funded',
        'new_info',
        'comments',
        'favo_users',
        'img_tags',
        'cnt_words',
        'fb_reaction',
        'fb_comment',
        'fb_share',
        'hatena_bookmark'
    ])

copyfile('{}/crowdfunding_data.csv'.format(root_path), '{}/crowdfunding_data_with_sns.csv'.format(root_path))

def main():
    """
    成功したプロジェクトは残っているが、失敗はない
    できればhtml保存したい
    """
    print("Start!!")
    sc.api_call(
        "chat.postMessage",
        channel="#general",
        text="<!here>Start! {}".format(exec_date)
    )

    project_urls = []
    page_cnt = 1
    # 検索ページからプロジェクトページを総取得
    print('Crawling search results')
    while True:
        url = 'https://readyfor.jp/projects?page={}'.format(page_cnt)
        timewait = 64
        time.sleep(2)
        while True:
            try:
                res = requests.get(url)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                sc.api_call(
                    "chat.postMessage",
                    channel="#general",
                    text="<!here> 検索ページの取得に失敗しています。{}秒後再取得します。\nURL: {}".format(timewait, url)
                )
                time.sleep(timewait)
                timewait = timewait*2
                continue
            break

        if "選択された条件のプロジェクトはありません" in res.text:
            break
        else:
            try:
                tmp_urls = scrape_project_url(res.text, page_cnt)
                project_urls.extend(tmp_urls)
                page_cnt += 1
                #page_cnt += 50 #Test
                continue
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                sc.api_call(
                    "chat.postMessage",
                    channel="#general",
                    text="<!here> scrape_project_urlでエラーが起きました。\nPage: {}\nDetail: {}".format(page_cnt, e.args)
                )
                break

    # プロジェクトページから欲しいデータを保存
    # htmlはディレクトリ作成して残したい
    print('Crawling project pages')
    id = 1
    for url in project_urls:
        time.sleep(2)
        timewait = 64
        while True:
            try:
                res = requests.get(url)
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                sc.api_call(
                    "chat.postMessage",
                    channel="#general",
                    text="<!here> プロジェクトページの取得に失敗しています。{}秒後再取得します。\nURL: {}".format(timewait, url)
                )
                time.sleep(timewait)
                timewait = timewait*2
                continue
            break
        if "こちらのプロジェクトの掲載は終了いたしました。" in res.text:
            continue
        else:
            # ページを保存し、スクレイピング
            filename = re.search(r"https://readyfor.jp/projects/(.+)$", url).group(1)
            with codecs.open('{}/html/{}.html'.format(root_path, filename), 'w', 'utf-8') as f:
                f.write(res.text)
            try:
                scrape_project_info(res.text, url, id)
                id += 1
                continue
            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                sc.api_call(
                    "chat.postMessage",
                    channel="#general",
                    text="<!here> scrape_project_infoでエラーが起きました。Skipします。\nURL: {}\nDetail: {}".format(url, e.args)
                )
                continue
    print("Scraping Done!!")
    sc.api_call(
        "chat.postMessage",
        channel="#general",
        text="<!here>Scraping Done! {}".format(exec_date)
    )

    sns_api()

    print("API request Done!!")
    sc.api_call(
        "chat.postMessage",
        channel="#general",
        text="<!here>API request Done! {}".format(exec_date)
    )
 
    with codecs.open('{}/crowdfunding_data_with_sns.csv'.format(root_path), 'r', 'utf-8') as f:
        sc.api_call(
            "files.upload",
            channels="#general",
            file=f,
            title="Upload data"
        )


def scrape_project_url(text, page):
    """
    検索ページからプロジェクトのURLをlistで返す
    """
    print('Scraping P.{}'.format(page))
    html = lxml.html.fromstring(text)
    project_urls = html.xpath('//article[contains(@class, "Entry")]/a')
    urls = ['https://readyfor.jp' + url.attrib['href'] for url in project_urls]

    return urls


def scrape_project_info(text, project_url, id):
    """
    プロジェクトページをスクレイプし、csvに書き込む
    """
    print('Scraping {}'.format(project_url))
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
        None,
        None,
        None,
        None
    ]

    # 仮にcsvでデータ保存

    with codecs.open('{}/crowdfunding_data.csv'.format(root_path), 'a', 'utf-8') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(project_info_data)

    print('Write on crowdfunding_data.csv')


def sns_api():
    # いいね数やブクマ数はapiにリクエスト
    print('Get FB HB API response')
    with codecs.open('{}/crowdfunding_data.csv'.format(root_path), 'r', 'utf-8') as f:
        f = csv.reader(f, lineterminator='\n')
        next(f)
        for record in f:
            project_url = record[2]
            days_to_go = record[11]
            print('Page: {}'.format(project_url))
            if days_to_go == '終了しました':
                print('プロジェクトは終了しています')
                with codecs.open('{}/crowdfunding_data_with_sns.csv'.format(root_path), 'a', 'utf-8') as f:
                    writer = csv.writer(f, lineterminator='\n')
                    writer.writerow(record)
                continue
            time.sleep(6)
            trying = 1
            fb_api_res = requests.get("https://graph.facebook.com/v3.0/?id={}&fields=engagement&access_token={}".format(project_url, FB_API_TOKEN)) 
            while 'error' in fb_api_res.json():
                sc.api_call(
                    "chat.postMessage",
                    channel="#general",
                    text="<!here> FB APIで取得に失敗しています。 {}回目".format(trying)
                )
                time.sleep(3600)
                fb_api_res = requests.get("https://graph.facebook.com/v3.0/?id={}&fields=engagement&access_token={}".format(project_url, FB_API_TOKEN)) 
                trying += 1
                if trying > 3:
                    return None
                    sc.api_call(
                        "chat.postMessage",
                        channel="#general",
                        text="<!here> 取得を中断します".format(trying)
                    )
            print(fb_api_res.json())
            fb_reaction = fb_api_res.json()['engagement']['reaction_count']
            fb_comment = fb_api_res.json()['engagement']['comment_count']
            fb_share = fb_api_res.json()['engagement']['share_count']
            hatena_api_res = requests.get("http://api.b.st-hatena.com/entry.count?url={}".format(project_url))
            timewait = 64
            while True:
                try:
                    hatena_bookmark = int(hatena_api_res.text)
                except ValueError:
                    hatena_bookmark = 0
                except Exception as e:
                    traceback.print_exc(file=sys.stdout)
                    time.sleep(timewait)
                    timewait = timewait*2
                    continue
                break
            record[-4], record[-3], record[-2], record[-1] = fb_reaction, fb_comment, fb_share, hatena_bookmark
            print('Write on crowdfunding_data_with_sns.csv')
            with codecs.open('{}/crowdfunding_data_with_sns.csv'.format(root_path), 'a', 'utf-8') as f:
                writer = csv.writer(f, lineterminator='\n')
                writer.writerow(record)


if __name__ == '__main__':
    main()

