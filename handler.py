import re
import requests

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
        response = requests.get(urls[0])
        print("Request Status:", response.status_code)
    else:
        print("No Url")