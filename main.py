from bs4 import BeautifulSoup
import requests
import json
import re
import datetime as dt
import pandas as pd
import sys

def hichart_js_format(script_text, chart_type):
    # Find specific chart in Hichart script
    # To convert javascript object to JSON format, with some processing
    # Return result as python dictionary

    target_section = False
    block = ""
    end_block = ""
    end_block_function = ""
    script_header = "Highcharts.chart('" + chart_type + "', "

    for line in script_text.splitlines():
        if chart_type in line:
            target_section = True
            end_block = ' ' * re.match(r"\s*", line).group().count(' ') + '});'
        if target_section:
            if 'function' in line:
                function_section = True
                end_block_function = ' ' * re.match(r"\s*", line).group().count(' ' ) + '}'
            if not function_section:
                block += re.sub(r'^(.*)//(.*)$', r'\1', line).rstrip().lstrip()

        if line.rstrip() == end_block_function:
            function_section = False
        if line.rstrip() == end_block:
            target_section = False
    if block:
        base = block.lstrip()[len(script_header):-2]
        key_cnv = re.sub(r'(\w+?):', r'"\1":', base)
        value_cnv = re.sub(r':\s?\'(.*?)\'(,|\s?})', r': "\1"\2', key_cnv)
        format_block = re.sub(r',\s?}', r'}', re.sub(r'\\\'', '', value_cnv))
        return(json.loads(format_block))

def get_chart_script(channel, chart_type):
    # Crawling "Detailed Statistics" page about each Youtube channel at SocialBlade.com
    # Find "Highcharts" from HTML, which draws statistic graph

    session = requests.Session()
    target_url = 'https://socialblade.com/youtube/channel/' + channel + '/monthly'
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'}
    html = session.get(target_url, headers=headers)
    soup = BeautifulSoup(html.text, 'html.parser')
    result = {}
    for script in soup.find_all('script'):
        script_text = str(script)
        if 'Highcharts.chart' in script_text:
            result = hichart_js_format(script_text, chart_type)
    return(result)

def microsecond_unixtime_to_timestamp(micros, mode):
    # SocialBlade.com provide timestamp as unixtime with microseconds
    # And those timezone is PST (-5:00 Hour)
    # Convert timezone PST to JST here

    second_unixtime = dt.datetime.fromtimestamp(micros / 1000)
    timestamp = second_unixtime.replace(tzinfo=dt.timezone(dt.timedelta(hours=-5)))
    jst_timestamp = timestamp.astimezone(dt.timezone(dt.timedelta(hours=9)))
    if mode == 'weekly':
        return(dt.date(jst_timestamp.year, jst_timestamp.month, jst_timestamp.day))
    elif mode == 'monthly':
        return(dt.date(jst_timestamp.year, jst_timestamp.month, 1))
    else:
        return(jst_timestamp)

def get_target_channels(filepath):
    # Get channel id from local file
    # The file include channel id and channel name as JSONNL(line-separated JSON) format
    # Return result as list of dictionary

    channels = []
    with open(filepath) as f:
        lines = f.read().rstrip('\n').split('\n')
        for line in lines:
            channels.append(json.loads(line))

    return(channels)

if __name__ == '__main__':
    # Get specific chart data from SocialBlade.com
    # Store each data to DataFrame and merge by timestamp
    # Export to CSV

    mode = sys.argv[1]
    channels_filepath = './channels.json'
    export_filepath = './social_blade_result.csv'
    if mode == 'weekly':
        chart_type = 'graph-youtube-daily-weekly-subscribers-container'
    elif mode == 'monthly':
        chart_type = 'graph-youtube-monthly-subscribers-container'

    channels = get_target_channels(channels_filepath)
    result = pd.DataFrame(data=None, index=None, columns=None, dtype=None, copy=False)
    dfs = []
    for channel in channels:
        channel_id = channel['channel_id']
        name = channel['name']
        script = get_chart_script(channel_id, chart_type)
        df = pd.DataFrame(list(script['series'][0]['data']), columns = ['timestamp', name])
        df['timestamp'] = df['timestamp'].apply(microsecond_unixtime_to_timestamp, mode=mode)
        dfs.append(df)
    for d in dfs:
        if result.empty:
            result = d
        else:
            result = pd.merge(result, d, on='timestamp', how='outer')

    result.to_csv(export_filepath)

