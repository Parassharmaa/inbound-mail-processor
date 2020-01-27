import re
import urllib.request

headers = {
    'User-Agent':
    'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.27 Safari/537.17'
}


def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']

    # preprocess email content
    message = message.replace("\\r", " ").replace("\\n", " ")

    # extract list of all urls starting with http:// or https://
    urls = re.findall(
        'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        message)

    print("All urls:", urls)
    if len(urls):
        req = urllib.request.Request(urls[0], headers=headers)
        resp = urllib.request.urlopen(req)
        print("Request Status:", resp.status)
    else:
        print("No Url")