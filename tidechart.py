#!/usr/bin/python3

from astral import LocationInfo
from astral.sun import sun
from datetime import date, time, datetime, timezone, timedelta
import pytz
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from scipy.interpolate import make_interp_spline, BSpline
east = pytz.timezone('US/Eastern')
matplotlib.rcParams['timezone'] = 'US/Eastern'

def sun_info(gps_lat, gps_long, astralevent):
    city = LocationInfo("Medford", "USA", "US/Eastern", gps_lat, gps_long)
    s = sun(city.observer, date=datetime.today(), tzinfo=city.timezone)[astralevent]
    return (s)


def load_file(filename='./bostontides_2020-2022.csv'):
    tides = pd.read_csv(filename)
    tides['Timestamp'] = pd.to_datetime(tides['Timestamp'],utc=True)
    tides = tides[['Timestamp','High/Low','Pred(Ft)']]
    tides['LocalTimestamp'] = tides['Timestamp'].apply(lambda x:x.tz_convert('US/Eastern'))
    return(tides)

def tideString(df, ts_tide, ts_date):
    time_min = east.localize(datetime.combine(ts_date, time(hour=0, minute=1)))
    time_max = east.localize(datetime.combine(ts_date, time(hour=23, minute=59)))
    df = df.loc[(df['LocalTimestamp'] > time_min) & (df['LocalTimestamp'] < time_max)]
    df = df[df['High/Low']== ts_tide].reset_index(drop=True)
    if len(df) > 1:
        tide_string = df['LocalTimestamp'][0].strftime("%I:%M%p") + " and " + df['LocalTimestamp'][1].strftime("%I:%M%p")
    else: 
        tide_string = df['LocalTimestamp'][0].strftime("%I:%M%p")
    return (tide_string)

def tideHeights(df, ts_date, t_delta):
    time_min = east.localize(datetime.combine(ts_date + timedelta(days=-t_delta), time(hour=0, minute=1)))
    time_max = east.localize(datetime.combine(ts_date + timedelta(days=+t_delta), time(hour=23, minute=59)))
    df = df.loc[(df['LocalTimestamp'] > time_min) & (df['LocalTimestamp'] < time_max)]
    return df[['Timestamp','Pred(Ft)']]

def savechart(df, sunrise, sunset):
    myFmt = mdates.DateFormatter('%I %p')
    x_min = east.localize(datetime.combine(date.today(), time(sunrise.hour-2, sunrise.minute)))
    x_max = east.localize(datetime.combine(date.today(), time(sunset.hour+2, sunset.minute)))

    y_max =  (df['Pred(Ft)'].max())
    y_min =  (df['Pred(Ft)'].min())
    
    fig = plt.figure()  # an empty figure with no axes
    fig.suptitle('No axes on this figure')  # Add a title so we know which it is
    
    fig, ax = plt.subplots(1, 1)

    ax.set_xlim([x_min, x_max])
    ax.set_ylim([y_min, y_max])

    x = df['Timestamp']
    y = df['Pred(Ft)']

    xnew = np.linspace(pd.Timestamp(x_min).value,pd.Timestamp(x_max).value,90) #300 represents number of points to make between T.min and T.max
    xnew = pd.to_datetime(xnew)
    spl = make_interp_spline(x, y, k=3) #BSpline object
    x_wave = spl(xnew)
    ax.plot(xnew, x_wave, markerfacecolor='dodgerblue', color='black')

    #set axis labels to time
    ax.xaxis.set_major_formatter(myFmt)
    ax.set_facecolor('ivory')
    ax.fill_between(xnew, x_wave, y2=y_min, where=None, interpolate=False,facecolor='dodgerblue', alpha=1, zorder=10)
    ax.axvspan(x_min, sunrise, alpha=0.2, color='blue', zorder=15)
    ax.axvspan(x_max, sunset, alpha=0.2, color='blue', zorder=15)
    ax.set_title("Tide and Daylight Forecast: ")
    ax.set_yticklabels([])
    ax.set_yticks([])

    plt.savefig('tide_chart_new.png', bbox_inches='tight')
    return()

def main():
    gps_lat = 42.4187
    gps_long = -71.1048

    sunrise = sun_info(gps_lat, gps_long,"sunrise")
    sunset = sun_info(gps_lat, gps_long,"sunset")

    tideinfo = load_file()
    df = tideHeights(tideinfo, date.today(), 1)
    savechart(df, sunrise, sunset)
    
    print ("High Tides:" + tideString(tideinfo,"High Tide",date.today()))
    print ("Low Tides:" + tideString(tideinfo,"Low Tide",date.today()))


if __name__ == "__main__":
    main()