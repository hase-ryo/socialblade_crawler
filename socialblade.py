from bs4 import BeautifulSoup
import requests
import json
import re
import datetime as dt
import pandas as pd

def hichart_js_format(script_text, chart_type):
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
        format_block = re.sub(r',\s?}', r'}', re.sub(r'\'(.*?)\'', r'"\1"', re.sub(r'(\w+):', r'"\1":', block.lstrip()[len(script_header):-2])))
        return(json.loads(format_block))

def get_weekly_subscriber(channel, chart_type, session):
    target_url = 'https://socialblade.com/youtube/channel/' + channel + '/monthly'
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'}
    html = session.get(target_url, headers=headers)
    soup = BeautifulSoup(html.text, 'html.parser')
    result = {}
    for script in soup.find_all('script'):
        script_text = str(script)
        if 'Highcharts.chart' in script_text:
            result = hichart_js_format(script_text, chart_type)
    print(result)
    return(result)

def microsecond_unixtime_to_timestamp(micros):
    second_unixtime = dt.datetime.fromtimestamp(micros / 1000)
    # convert EST (-5 hour) to UTC (0 hour)
    utc_timestamp = second_unixtime.replace(tzinfo=dt.timezone(dt.timedelta(hours=-5)))
    # convert UTC to JST(+9 hour)
    jst_timestamp = utc_timestamp.astimezone(dt.timezone(dt.timedelta(hours=9)))
    return(jst_timestamp)

if __name__ == '__main__':
    session = requests.Session()
    channel = 'UCoSrY_IQQVpmIRZ9Xf-y93g'
    # channel = 'UCAWSyEs_Io8MtpY3m-zqILA'
    chart_type = 'graph-youtube-daily-weekly-subscribers-container'
    # chart_type = 'graph-youtube-daily-weekly-vidviews-container'
    res = get_weekly_subscriber(channel, chart_type, session)
    df = pd.DataFrame(list(res['series'][0]['data']), columns=['week', 'subscriber'])
    print(df)
