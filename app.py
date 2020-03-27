import feedparser
import time
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import requests
from decimal import Decimal

chatId = os.getenv('TELEGRAM_CHAT_ID', '')
token = os.getenv('TELEGRAM_TOKEN', '')

def sendTelegramMessage(entry):
    text = f"#OzBargain {entry.title} {entry.link}"

    requestBody = {
        "chat_id": chatId,
        "text": text
    }
    print("Send message: ", text)
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    r = requests.post(url, json=requestBody)
    print(f"Message status code: {r.status_code}")


def sendMessageIfFound(entries, last_feed_time):
    for entry in entries:
        feed_time = Decimal(time.mktime(entry.published_parsed))
        if  feed_time - last_feed_time > 0:
            sendTelegramMessage(entry)
            

def start(event, context):
    print("Received request to check rss feed")

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("Things")

    response = table.query(
        KeyConditionExpression=Key('Type').eq('OzBargainFeed')
    )

    for item in response['Items']:
        key = item['Key']
        url = item['Url']

        print(f"Checking feed of {key} at {url}")

        feeds = feedparser.parse(url)
        print(f"Found {len(feeds.entries)} for {key}")

        first_time = item['FirstTime']
        last_feed_time = item['LastFeedTime']

        if not first_time:
            print(f"Start checking all feeds since {last_feed_time}")
            sendMessageIfFound(feeds.entries, last_feed_time)
        
        last_feed_time = max(time.mktime(entry.published_parsed) for entry in feeds.entries)
        print(f"Updating Last Feed Time to {last_feed_time}")

        table.update_item(
            Key={
                'Type': 'OzBargainFeed',
                'Key': key
            },
            UpdateExpression='SET LastFeedTime = :val1, FirstTime = :val2',
            ExpressionAttributeValues={
                ':val1': Decimal(last_feed_time),
                ':val2': False
            }
        )
    
    print("All Ozbargain items are checked")


if __name__ == "__main__":
    start(None, None)