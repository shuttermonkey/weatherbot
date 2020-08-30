#!/usr/bin/python3

from PIL import Image, ImageDraw, ImageFont
import textwrap
import tidechart
from noaa_sdk import noaa
import requests
from datetime import date, datetime, timedelta, time, timezone

import matplotlib
matplotlib.use('Agg') #don't print to terminal
matplotlib.rcParams['timezone'] = 'US/Eastern'
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import scipy
import scipy.interpolate as sp
from scipy.interpolate import make_interp_spline

import pytz
import re

import os
from dotenv import load_dotenv
load_dotenv()

tweet = False # set this to True to tweet 

if tweet == True:
    import twitter

myFmt = mdates.DateFormatter('%-I %p') #it's 5 PM somewhere


gps_lat = 42.4187
gps_long = -71.1048
local_tz = pytz.timezone('US/Eastern')

tomorrow = date.today() + timedelta(days = 1) 
dt = datetime.today ()




def forecast_data(gps_lat, gps_long):
    n = noaa.NOAA()
    return (n.points_forecast(gps_lat, gps_long, hourly=False))

def startOffset(forecast):
    start_period = 0    
    #Only want daytime info
    if (forecast['properties']['periods'][0]['isDaytime']) == False:
        start_period = 1
    return (start_period)

def precipitationGuess(forecast):
    detailed_forecast = forecast['properties']['periods'][0]['detailedForecast']
    try:
        found = re.search('Chance of precipitation is (.+?)%.', detailed_forecast).group(1)
    except AttributeError:
        found = 0 # apply your error handling
    if found != 0:
	    PrecipChance = ("Precip Chance: " + str(found) + "%") + "\n"
    else:
	    PrecipChance = ""
    return PrecipChance

def get_forecast_icons(forecast, start_period):
    for i in range (6):
        print(forecast['properties']['periods'][(i*2) + start_period]['name'] + ": " + forecast['properties']['periods'][(i*2) + start_period]['shortForecast'])
        iconURL = forecast['properties']['periods'][(i*2) + start_period]['icon'].replace("medium","large")
        Picture_request = requests.get(iconURL)
        if Picture_request.status_code == 200:
            picName = "./" + str(i) + ".png"
            with open(picName, 'wb') as f:
                f.write(Picture_request.content)

def createArray(forecast, field, start_period):
    arr = []
    for i in range (12):
        param = forecast['properties']['periods'][(i) + start_period][field]
        arr.append(param)
    return(arr)

def forecast_days(s):
    #returns next 5 days (eg ['MON','TUE','WED','THU','FRI'])
    arr=[]
    for i in range(5):
        arr.append(s[(i*2)+2][0:3].upper())
    return(arr)

def minMaxforecast(s):
    #returns next 5 days temp in min/max format (eg ['68/85','65/90','67/72'...])
    arr=[]
    for i in range(5):
        arr.append(str(min(s[(i*2)+2],s[(i*2)+3]))+"/"+str(max(s[(i*2)+2],s[(i*2)+3])))
    return(arr)


def addThumbnail (tn_img, bg_img, x_offset, y_offset):
    bg_img.paste(tn_img, (x_offset, y_offset))
    return bg_img
    #img2.save('PIL_output.png',"PNG")

def todayForecastText (img, t_now, t_max, t_min, t_desc, t_date):
    font_big = ImageFont.truetype('Biryani-Regular.ttf',100)
    font_med = ImageFont.truetype('Biryani-Regular.ttf',36)
    font_small = ImageFont.truetype('Biryani-Regular.ttf',26)
    t_desc = "\n".join(textwrap.wrap(t_desc, width=40)) 

    draw = ImageDraw.Draw(img)
    draw.text((75, 100), str(t_date), font=font_med, fill="#555555")
    draw.text((225, 130), str(t_now), font=font_big, fill="#000055")
    draw.text((230, 240), str(t_min) + '/' + str(t_max), font=font_med, fill="#555555")
    draw.text((60, 300), str(t_desc), font=font_small, fill="#333333")
    return img

def addForecastThumbnails(img, x_init, y_init, x_offset):
    for i in range(5):
        tn_img = Image.open(str(i+1)+".png")
        x_loc =  x_init + (int(i) * x_offset)
        y_loc = y_init
        img = addThumbnail(tn_img, img, x_loc, y_loc)
    return img

def addForecastText(img, mydays, temp, x_init, y_init, x_offset):
    font = ImageFont.truetype('Biryani-Regular.ttf',40)
    draw = ImageDraw.Draw(img)
    for i in range(5):
        x_loc =  x_init + (int(i) * x_offset)
        y_loc = y_init
        draw.text((x_loc+20, y_loc-60), mydays[i], font=font, fill="#ffffee")
        draw.text((x_loc+10, y_loc+130), temp[i], font=font, fill="#ffffee")
    return img

def addTideChart(img):
    chart = Image.open("tide_chart_new.png")
    img = addThumbnail(chart, img, 610, 100)
    return img

def addTideText(img,ht,lt,sr,ss):
    font = ImageFont.truetype('Biryani-Regular.ttf',28)
    draw = ImageDraw.Draw(img)
    mytext = sr+"\n"+ss+"\n"+ht+"\n"+lt
    draw.text((620, 530), mytext, font=font, fill="#333333")
    return img

def sendTweet(tweetString):
    consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
    consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    with open("out.png", "rb") as imagefile:
        imagedata = imagefile.read()
        my_twitter_auth = twitter.OAuth(access_token, access_token_secret, consumer_key, consumer_secret)
        twit = twitter.Twitter(auth=my_twitter_auth)
        t_upload = twitter.Twitter(domain='upload.twitter.com', auth=twitter.OAuth(access_token, access_token_secret, consumer_key, consumer_secret))
        id_img = t_upload.media.upload(media=imagedata)["media_id_string"]
        twit.statuses.update(status=tweetString, media_ids=id_img)

def main():
    datestring  = datetime.today().strftime('%a %-d %b %Y')
    forecast = forecast_data(gps_lat,gps_long)
    start_period = startOffset(forecast)
    get_forecast_icons(forecast,start_period)
    sunrise = tidechart.sun_info(gps_lat, gps_long,"sunrise")
    sunset = tidechart.sun_info(gps_lat, gps_long,"sunset")
    str_sunrise = 'Sunrise: ' +  tidechart.sun_info(gps_lat, gps_long,"sunrise").strftime("%I:%M%p")
    str_sunset = 'Sunset: ' +  tidechart.sun_info(gps_lat, gps_long,"sunset").strftime("%I:%M%p")
    today_desc = forecast['properties']['periods'][0]['detailedForecast']
    today_max = max(forecast['properties']['periods'][0]['temperature'],forecast['properties']['periods'][1]['temperature'])
    today_min = min(forecast['properties']['periods'][0]['temperature'],forecast['properties']['periods'][1]['temperature'])
    today_now = forecast['properties']['periods'][0]['temperature']
    txt_days = (forecast_days(createArray(forecast, 'name', start_period)))
    temps = (minMaxforecast(createArray(forecast, 'temperature', start_period)))
    tideinfo = tidechart.load_file()
    h_tides= ("High Tides:" + tidechart.tideString(tideinfo,"High Tide",datetime.today()))
    l_tides= ("Low Tides:" + tidechart.tideString(tideinfo,"Low Tide",datetime.today()))
    tidechart.savechart(tideinfo, sunrise, sunset)

    tn = Image.open('0.png')
    bg = Image.open('medford_bg.png')
    pil_output = addThumbnail (tn, bg, 75,170)
    pil_output = addForecastThumbnails(pil_output, 60, 800, 240)

    pil_output = addForecastText(pil_output, txt_days, temps, 60,800,242)
    pil_output = todayForecastText(pil_output,today_now, today_max,today_min, today_desc,datestring)
    pil_output = addTideChart(pil_output)
    pil_output = addTideText(pil_output,h_tides,l_tides,str_sunrise,str_sunset)

    pil_output.save('out.png',"PNG")

    sForecast = forecast['properties']['periods'][start_period]['shortForecast']
    tweetString = ( 'Today\'s #MedfordMA Forecast\n Temp: ' + str(today_min) + " to " + str(today_max) + "\n " + sForecast + "\n " + precipitationGuess(forecast) )

    if tweet == True:
        sendTweet(tweetString)
    else:
        print(tweetString)

if __name__ == "__main__":
    main()

