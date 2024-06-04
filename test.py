import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
import urllib
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import datetime
import csv
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

url = os.environ["site_url"] #対象の美容院のスタッフページ
simei_name=os.environ["simei_name"] #指名する人間の名前
x=2 #施術メニューが上から何番目にあるか

#クロム処理
driver=webdriver.Chrome() #クロムを起動

driver.get(url) #URLを取得
sleep(1) #取得まで待機

simei=driver.find_element(By.LINK_TEXT,simei_name).click() #指名者の名前のボタンをHTMLから取得しクリック
sleep(1)

couse=driver.find_element(By.LINK_TEXT,"指名して予約する").click() #指名して予約するボタンをHTMLから取得しクリック
sleep(1)

couse1=driver.find_elements(By.CLASS_NAME,"mT10")[x-1] #メニューリストからｘ番目のメニューを抽出
couse2=couse1.find_element(By.PARTIAL_LINK_TEXT,"空席確認").click() #該当メニューの空席確認ボタンを取得

try:
    def check(): #任意の指名者の任意のメニューの全空席日時のhrefをリストに格納する関数
        opens_list=[] #空席日時のhrefのリスト
        for r in range(4): #全ページに反復処理
            opens=driver.find_elements(By.CLASS_NAME,"open") #空席日時のクラスを全てリスト型で抽出
            for i in opens: #空席日時のクラスからhrefを抽出しリストに格納していく反復処理
                opens_href=i.find_element(By.TAG_NAME,"a").get_attribute("href") #aタグからhrefを抽出
                opens_list.append(opens_href)
            driver.find_element(By.PARTIAL_LINK_TEXT,"次の一週間").click()
        return opens_list

    opens_list=(check()) #空席日時のhrefのリスト

    def apo_day(hreflist): #hrefの文字列から空席日時を抽出する関数
        blank=[] #空席日時のリスト
        for u in hreflist:#hrefのリストから空席日時の情報を取り出す反復処理
                que=parse_qs(urlparse(u).query) #クエリのみを辞書型で抽出
                qu=("".join(que["rsvRequestDate1"]))+("".join(que["rsvRequestTime1"])) #日付と時間表記の値のみを抽出しリスト表記を除去
                day=(datetime.datetime.strptime(qu,"%Y%m%d%H%M")) #時間型に変更
                blank.append(day)
        return blank

    days=(apo_day(opens_list)) #空席日時のリスト
    sleep(1)
    driver.close() #クロム終了

except: #上記の処理のエラーをlineで送る
    urll=os.environ["line_url"] #line設定
    access=os.error["access_key"]
    header={"Authorization": "Bearer" + " " +access}

    message="クロムエラー" 
    send={"message":message}
    requests.post(urll,headers=header,params=send,)
    

links=list() #空席のhrefのリスト
old_links=set() #古いデータ
new_links=set() #新しいデータ

#空席日時のhrefのリストを新たなリストに格納する反復処理
for u in opens_list: 
    links.append(u)

with open (os.environ["csv"],"r")as e: #csvを読み取る
    reader=csv.reader(e)
    for r in reader: #csvの情報を古いデータとする
        old_links=set(r)

with open(os.environ["csv"],"w")as e:#csvに書き出す
    writer=csv.writer(e,lineterminator="\n")
    writer.writerow(links) #csvの一行目に上書き

new_links=set(links) #空席日時のhrefのリストを新しいデータとする


if(old_links==new_links): #古いデータと新しいデータが一緒ならスルー
    pass
else: #キャンセル発生時の処理
    added=new_links-old_links #異なる場合は追加されたものを抽出＝キャンセルされた日程のHTML
    added_=[] #htmlから日程を文字列で取得し格納
    for i in apo_day(list(added)):
        added.append(str(i))

    #line設定
    urll=os.environ["line_url"] #line設定
    access=os.error["access_key"]
    header={"Authorization": "Bearer" + " " +access}
    
    #キャンセルが出た場合にキャンセル日をlineで送る
    message="キャンセルが出ました。\n "+str(sorted(added_)) 
    send={"message":message}
    requests.post(urll,headers=header,params=send,)
    
    #キャンセル日時を日程順に並べかえた文字列のリスト
    add_days=[] 
    for i in (apo_day(list(added))): #キャンセル日時のリストから時間型を文字列で生成する反復処理
        add_days.append(str(i))
    sort_days=(sorted(add_days))#日程順にする

    #キャンセル日時の日付のみ文字列で抽出したリスト
    add_day=[] 
    for i in sort_days: 
        da=datetime.datetime.strptime(i,"%Y-%m-%d %H:%M:%S") #時間型にする
        day=da.date() #日付だけ抽出
        add_day.append(str(day))

    #時間のみ文字列で抽出したリスト
    add_time=[] 
    for i in sort_days: 
        tim=datetime.datetime.strptime(i,"%Y-%m-%d %H:%M:%S") #時間型にする
        time=tim.time() #時間だけ抽出
        add_time.append(str(time))

    #曜日を抽出したリスト
    add_week=[datetime.datetime.strptime(i,"%Y-%m-%d %H:%M:%S").strftime("%a")for i in add_days] 

    #キャンセル発生時間帯を格納したリスト
    canceltime=[] 
    for i in range(len(add_days)): #キャンセル日数分現在時刻の時間帯をリストに格納
        dt=datetime.datetime.now()
        canceltime.append(dt.time)

    #現在時刻とキャンセル日の差のリスト
    before=[] 
    for i in add_days:
        p=abs(datetime.datetime.now()-datetime.datetime.strptime(i,"%Y-%m-%d %H:%M:%S")) #現在時刻とキャンセル時刻の減法
        pp=int(p.total_seconds()) #差の秒数の小数点切り捨て
        pr=(datetime.timedelta(seconds=pp)) #日時表記に変更
        before.append(pr)

    #天気予報サイトからキャンセル日のデータを抽出
    weather_url="https://tenki.jp/forecast/3/16/4410/13101/10days.html" #天気予報サイト
    res=requests.get(weather_url)
    soup=BeautifulSoup(res.text,"html.parser") #URLの解析

    tenki=soup.find_all(class_="days") #天気予報サイトから特定の日付のデータを抽出
    weathers=[] #キャンセル日の天気予報
    for e in add_day:        
        for i in tenki:
            if (e[5:7]+"月"+e[8:10]+"日("in i): #キャンセル日リストから抽出した日付を含むデータを抽出
                mark=((i.parent).find("img")) #そのデータの親要素から天気マークを抽出
                weather=(mark.attrs["alt"]) #天気予報文字列を取得
                weathers.append(weather)
            else:
                pass

    #データベースに接続
    user=os.environ["user"]
    password=os.environ["password"]
    host=os.environ["host"]
    port=os.environ["port"]
    base=os.environ["databese"]
    
    connection_config={"user":user,"password":password,"host":host,"port":port,"database":base}
    engine=create_engine('postgresql://{user}:{password}@{host}:{port}/{database}'.format(**connection_config))
    connection=psycopg2.connect( host="host",user="user",password="password",port="port",database="database" )
    cursor=connection.cursor()
    for d,a,y,s,h,b,w in zip(add_day,add_day,add_time,add_week,canceltime,before,weathers): #データテーブルに新しいキャンセル日の情報を追加
        cursor.execute("INSERT INTO test_table01(日時,日付,時間,曜日,発生時間帯,時間差,天気) values(%s,%s,%s,%s,%s,%s,%s)",(d,a,y,s,h,b,w))
        connection.commit()

    #データベース終了
    cursor.closed()
    connection.close()



