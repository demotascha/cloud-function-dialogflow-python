import os
import apiai
import json
import requests
import random

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage,
    LocationMessage,
    CarouselTemplate, CarouselColumn, URIAction,
    TemplateSendMessage, ButtonsTemplate, URITemplateAction,
)

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
SECRET = os.environ.get('SECRET')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
DIALOGFLOW_CLIENT_ACCESS_TOKEN = os.environ.get('DIALOGFLOW_CLIENT_ACCESS_TOKEN')

ai = apiai.ApiAI(DIALOGFLOW_CLIENT_ACCESS_TOKEN)
line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(SECRET)

def callback(request):
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    print("Request body: " + str(body))

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ================= 客製區 Start =================
def is_alphabet(uchar):
    if ('\u0041' <= uchar<='\u005a') or ('\u0061' <= uchar<='\u007a'):
        print('English')
        return "en"
    elif '\u4e00' <= uchar<='\u9fff':
        #print('Chinese')
        print('Chinese')
        return "zh-tw"
    else:
        return "en"
# ================= 客製區 End =================


# ================= 機器人區塊 Start =================
@handler.add(MessageEvent, message=TextMessage)  # default
def handle_text_message(event):                  # default
    msg = event.message.text # message from user
    uid = event.source.user_id # user id
    # 1. 傳送使用者輸入到 dialogflow 上
    ai_request = ai.text_request()
    #ai_request.lang = "en"
    ai_request.lang = is_alphabet(msg)
    ai_request.session_id = uid
    ai_request.query = msg

    # 2. 獲得使用者的意圖
    ai_response = json.loads(ai_request.getresponse().read())
    user_intent = ai_response['result']['metadata']['intentName']

    # 3. 根據使用者的意圖做相對應的回答
    if user_intent == "WhatToEat": # 當使用者意圖為詢問午餐時
        # 建立一個 button 的 template
        buttons_template_message = TemplateSendMessage(
            alt_text="Please tell me where you are",
            template=ButtonsTemplate(
                text="Please tell me where you are",
                actions=[
                    URITemplateAction(
                        label="Send my location",
                        uri="line://nv/location"
                    )
                ]
            )
        )
        line_bot_api.reply_message(
            event.reply_token,
            buttons_template_message)

    elif user_intent == "WhatToPlay": # 當使用者意圖為詢問遊戲時
        msg = "Hello, it's not ready"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg))

    else: # 聽不懂時的回答
        msg = "Sorry，I don't understand"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=msg))

@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    # 獲取使用者的經緯度
    lat = event.message.latitude
    long = event.message.longitude
    print(str(event))

    # 使用 Google API Start =========
    # 1. 搜尋附近餐廳
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?key={}&location={},{}&rankby=distance&type=restaurant&language=zh-TW".format(GOOGLE_API_KEY, lat, long)
    nearby_results = requests.get(nearby_url)
    # 2. 得到最近的20間餐廳
    nearby_restaurants_dict = nearby_results.json()
    top20_restaurants = nearby_restaurants_dict["results"]
    ## CUSTOMe choose rate >= 4
    res_num = (len(top20_restaurants)) ##20
    above4=[]
    for i in range(res_num):
        try:
            if top20_restaurants[i]['rating'] > 3.9:
                # print('rate: ', top20_restaurants[i]['rating'])
                above4.append(i)
        except:
            KeyError
    if len(above4) < 0:
        print('no 4 start resturant found')
    # 3. 隨機選擇一間餐廳
        restaurant = random.choice(top20_restaurants)

    # 隨機選擇三間
    cc=[]
    count = 0
    while count < 3:
        restaurant = top20_restaurants[random.choice(above4)]
        # 4. 檢查餐廳有沒有照片，有的話會顯示
        if restaurant.get("photos") is None:
            thumbnail_image_url = None
        else:
            # 根據文件，最多只會有一張照片
            photo_reference = restaurant["photos"][0]["photo_reference"]
            thumbnail_image_url = "https://maps.googleapis.com/maps/api/place/photo?key={}&photoreference={}&maxwidth=1024".format(GOOGLE_API_KEY, photo_reference)
        # 5. 組裝餐廳詳細資訊
        rating = "無" if restaurant.get("rating") is None else restaurant["rating"]
        address = "沒有資料" if restaurant.get("vicinity") is None else restaurant["vicinity"]
        details = "評分：{}\n地址：{}".format(rating, address)

        # 6. 取得餐廳的 Google map 網址
        map_url = "https://www.google.com/maps/search/?api=1&query={lat},{long}&query_place_id={place_id}".format(
            lat=restaurant["geometry"]["location"]["lat"],
            long=restaurant["geometry"]["location"]["lng"],
            place_id=restaurant["place_id"]
        )
        # 建立 CarouselColumn obj
        c = CarouselColumn(
            thumbnail_image_url=thumbnail_image_url,
            title=restaurant["name"],
            text=details,
            actions=[
                URIAction(
                    label='查看 Google 地圖',
                    uri=map_url
                )
            ]
        )
        # 加入 list
        cc.append(c)
        count += 1

    # 回覆使用 Carousel Template
    carousel_template_message = TemplateSendMessage(
        alt_text='選出三間推薦給你',
        template=CarouselTemplate(
            columns=cc
        )
    )
    line_bot_api.reply_message(
        event.reply_token,
        carousel_template_message)