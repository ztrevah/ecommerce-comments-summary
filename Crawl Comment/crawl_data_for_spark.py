import requests
import pandas as pd
import time
import random
from tqdm import tqdm
import os

cookies = {
    'SPC_F':'6g4tsyNnAOVZrdkEothirX2vqOAKYKvG',
    'REC_T_ID':'1b90a284-60d7-11ee-9fac-347379167e6a',
    '_fbp':'fb.1.1696218749922.845714687',
    '_hjSessionUser_868286':'eyJpZCI6IjM4MDc4Mzk3LTkyYjktNWI5OC04ZTU5LTA5MTkwNDIzMjA2OCIsImNyZWF0ZWQiOjE2OTYyMTg3NTE3ODQsImV4aXN0aW5nIjp0cnVlfQ==',
    'SPC_CLIENTID':'Nmc0dHN5Tm5BT1Zakkvipnlfiezqpjbc',
    '_fbc':'fb.1.1696492052115.IwAR3s_t5R4-Eo_PkMsWA23tmIQDeOW5bBwvuO_HOdubaAe8_SnfMHKpCGk5I',
    'SPC_U':'-',
    'SPC_EC':'-',
    'SPC_R_T_ID':'aMpQVEaogeEgzC2REyIqgNf7HtAfXTZnpg/Na8ETLYtdN+zfyJVZmwkscsgLiaLubPk4wOZz2hiD/7WnGGPITLiSYjJQa7mrT1bjyaiL7dug9IU8hMEZeGmzlji2TQAnAABmEplJXni1v0TTuEElpSAcsxbTVdqiPg0HRgG1tzg=',
    'SPC_R_T_IV':'cDhScmF4ZHdmUTJEV3Nreg==',
    'SPC_T_ID':'aMpQVEaogeEgzC2REyIqgNf7HtAfXTZnpg/Na8ETLYtdN+zfyJVZmwkscsgLiaLubPk4wOZz2hiD/7WnGGPITLiSYjJQa7mrT1bjyaiL7dug9IU8hMEZeGmzlji2TQAnAABmEplJXni1v0TTuEElpSAcsxbTVdqiPg0HRgG1tzg=',
    'SPC_T_IV':'cDhScmF4ZHdmUTJEV3Nreg==',
    '_ga_M32T05RVZT':'GS1.1.1702584482.8.0.1702584482.60.0.0',
    '_gcl_au':'1.1.132621638.1704285163',
    'SPC_SEC_SI':'v1-Q0doV2lrOFBvRXR0c0tWUzqSIPnPlp6/s6X1lEQ6DmKult9Xnpyqiml+aAZ4WFrGQffJjLIlh/Q4Pfhzck2AF+XKvuVVoMsC17uQmkH/ukE=',
    'SPC_SI':'QQKdZQAAAAA4U21UOWc2cUgzIwAAAAAAUVg4ZjE0Y28=',
    '__LOCALE__null':'VN',
    'csrftoken':'HjkIff4F9AQvoVi8PQtF5REcH6U2DCWX',
    '_sapid':'4ca77247a7f4e72281a35b07b63eded22d2b34d5ddb91a83eab792c7',
    '_ga_4GPP1ZXG63':'GS1.1.1704943368.5.0.1704943368.0.0.0',
    '_QPWSDCXHZQA':'785dab59-3459-49bd-e656-dff710e22f59',
    'REC7iLP4Q':'81046d04-828d-428f-b5bf-41fd10567732',
    'shopee_webUnique_ccd':'8qu2xejEBqwAS28CkMddQA%3D%3D%7C6jucaHmWIlDbdL77vaMDskUuw4sN2oC6efijlAdrZZISf3l0wmtt5zPIFmFbyEIKP%2BfCr%2BojiZWQPQ%3D%3D%7CEbX67z8zoaWMskfm%7C08%7C3',
    'ds':'11970091b5c5d10f73297635039af2e2',
    'AMP_TOKEN':'%24NOT_FOUND',
    '_ga':'GA1.2.1754520024.1696218751',
    '_gid':'GA1.2.1338439444.1704943371',
    '_dc_gtm_UA-61914164-50':'1'

}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Accept': 'application/json',
    'Accept-Language': 'vi-VN,vi;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://shopee.vn/G%C4%83ng-Tay-%C4%91i-ph%C6%B0%E1%BB%A3t-511-Ng%C3%B3n-C%E1%BB%A5t-(Lo%E1%BA%A1i-X%E1%BB%8Bn)-T%E1%BA%ADp-Gym-L%C3%A1i-xe-%C4%90i-ph%C6%B0%E1%BB%A3t-i.163364638.9746994645?sp_atk=2fd4383f-0ce1-4acd-9f96-0c57fad2eb3c&xptdk=2fd4383f-0ce1-4acd-9f96-0c57fad2eb3c',
    'X-Csrftoken': 'HjkIff4F9AQvoVi8PQtF5REcH6U2DCWX',
    'Connection': 'keep-alive',
    'TE': 'Trailers',
}

params = {
    'exclude_filter': '1',
    'filter': '0',
   ' filter_size': '0',
    'flag': '1',
    'fold_filter': '0',
    'itemid': '9746994645',
    'limit': '50',
    'offset': '0',
    'relevant_reviews': 'false',
    'request_source': '2',
    'shopid': '163364638',
    'tag_filter': '',
    'type': '0',
    'variation_filters': ''

}

def comment_parser(file_json, star):
    d = dict()
    d['itemid'] = file_json.get('ratings')[star].get('itemid')
    d['name'] = file_json.get('ratings')[star].get('product_items')[0].get('name')
    d['shopid']  = file_json.get('ratings')[star].get('shopid')
    d['userid'] = file_json.get('ratings')[star].get('userid')
    d['rating_star'] = file_json.get('ratings')[star].get('rating_star')
    d['comment'] = file_json.get('ratings')[star].get('comment')

    return d
import os
import requests
import pandas as pd
import time
from tqdm import tqdm
import re

BASE_URL = 'https://shopee.vn/api/v2/item/get_ratings'
params = {
    'exclude_filter': '1',
    'filter': '0',
    'filter_size': '0',
    'flag': '1',
    'fold_filter': '0',
    'limit': '50', 
    'offset': '0',
    'relevant_reviews': 'false',
    'request_source': '2',
    'tag_filter': '',
    'type': '0',
    'variation_filters': ''
}

# Hàm lấy dữ liệu đánh giá
def make_request(item_id, shop_id, offset=0):
    params['itemid'] = item_id
    params['shopid'] = shop_id
    params['offset'] = offset
    response = requests.get(BASE_URL, headers=headers, params=params, cookies=cookies)
    print(response.status_code)
    response.raise_for_status()
    return response

def extract_ids_from_url(url):
    match = re.search(r'i\.(\d+)\.(\d+)', url)
    if match:
        shopid = match.group(1)
        itemid = match.group(2)
        return itemid, shopid
    return None, None

df_id = pd.read_csv('shopee_product_id.csv', header=None)
product_urls = df_id[0].tolist()

def crawl_comments(item_id, shop_id, max_reviews=100000):
    all_comments = []
    offset = 0
    while len(all_comments) < max_reviews:
        response = make_request(item_id, shop_id, offset)
        if not response:
            break
        json_data = response.json().get('data')
        ratings = json_data.get('ratings', [])
        if not ratings: 
            break
        for rating in ratings:
            comment = rating.get('comment', '').replace('\n', ' ').replace('\r', ' ')
            all_comments.append({
                'rating_star': rating.get('rating_star'),
                'comment': comment,
                'name': rating.get('product_items')[0].get('name') if rating.get('product_items') else ''
            })
        offset += 50
        time.sleep(0.2)

        if len(all_comments) % 50 == 0:
            df_comment = pd.DataFrame(all_comments[-50:]) 
            append_to_csv(df_comment, f'{item_id}_{shop_id}.csv')

    return all_comments

def append_to_csv(data, filename):
    if not os.path.exists(filename):
        data.to_csv(filename, mode='w', header=True, index=False)
    else:
        data.to_csv(filename, mode='a', header=False, index=False)
        
def save_file_to_hdfs(item_id, shop_id):
    params = {
        'user.name': 'chiennq',
        'op': 'CREATE'
    }
    headers = {
        "Content-Type": "application/octet-stream",
    }
    base_url = "http://192.168.146.16:14000/webhdfs/v1"
    file = open(f'{item_id}_{shop_id}.csv', 'rb')
    
    try:
        res = requests.delete(
            url=f'{base_url}/raw/{item_id}_{shop_id}.csv', 
            params={
                'user.name': 'chiennq',
                'op': 'DELETE'
            }
        )
    except:
        pass
    
    res = requests.put(url=f'{base_url}/raw/{item_id}_{shop_id}.csv', headers=headers, params=params, data=file.read())
    return res.status_code

def save_list_files_to_hdfs():
    params = {
        'user.name': 'chiennq',
        'op': 'CREATE'
    }
    headers = {
        "Content-Type": "application/octet-stream",
    }
    base_url = "http://192.168.146.16:14000/webhdfs/v1"
    file = open(f'list.csv', 'rb')

    try:
        res = requests.delete(
            url=f'{base_url}/list.csv', 
            params={
                'user.name': 'chiennq',
                'op': 'DELETE'
            }
        )
    except:
        pass

    res = requests.put(url=f'{base_url}/list.csv', headers=headers, params=params, data=file.read())
    return res.status_code

ids = []

for url in product_urls:
    item_id, shop_id = extract_ids_from_url(url)
    if item_id and shop_id: 
        ids.append(f"{item_id}_{shop_id}")

df_ids = pd.DataFrame(ids)

df_ids.to_csv('list.csv', index=False, header=False)

save_list_files_to_hdfs()

print("Danh sách item_id và shop_id đã được lưu vào list.csv dưới dạng 'itemid_shopid'.")
    
result = []

for url in tqdm(product_urls, desc='Crawling comments'):
    item_id, shop_id = extract_ids_from_url(url)
    if item_id and shop_id:
        print(f'Crawling comments for product {item_id} in shop {shop_id}')
        comments = crawl_comments(item_id, shop_id)
        result.extend(comments)
        save_file_to_hdfs(item_id, shop_id)
        

print("Data saved to shopee_comments_data.csv")

