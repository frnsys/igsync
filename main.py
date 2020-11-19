import re
import time
import json
import config
import tweepy
import requests
import facebook
import logging
from http import cookiejar
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# Regex for extracting the Javascript data loaded in Instagram
ig_data_re = re.compile('window\._sharedData = (.+)<\/script>')

tw_auth = tweepy.OAuthHandler(config.TW_CONSUMER_KEY, config.TW_CONSUMER_SECRET)
tw_auth.set_access_token(config.TW_ACCESS_TOKEN, config.TW_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(tw_auth)
fb_api = facebook.GraphAPI(access_token=config.FB_ACCESS_TOKEN)

# Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S %Z')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def download(url, outfile):
    """download a file"""
    fname = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(outfile, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush()
    return outfile


# TODO: might not actually be necessary? Twitter shortens automatically iirc
def shorten(url):
    resp = requests.post('https://api-ssl.bitly.com/v4/shorten', headers={
        'Authorization': 'Bearer {}'.format(config.BITLY_ACCESS_TOKEN),
        'Content-Type': 'application/json'
    }, json={
        'long_url': url,
    })
    data = resp.json()
    return data['link']


def main():
    # Load existing list of seen IG post ids
    try:
        seen = set(json.load(open('seen.json')))
    except FileNotFoundError:
        seen = set()

    # Instagram cookies, to prevent getting hit with a login screen
    cj = cookiejar.MozillaCookieJar('cookies.txt')
    cj.load()
    for cookie in cj:
        # Set cookie expire date to 14 days from now
        # to prevent dropping of any cookies with expires=0
        cookie.expires = time.time() + 14 * 24 * 3600

    # Get the Instagram profile page
    # and extract the JSON data
    resp = requests.get(config.IG_URL, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'
    }, cookies=cj)
    data = ig_data_re.search(resp.content.decode('utf8')).group(1)
    data = data.strip(';')
    data = json.loads(data)

    # Iterate over the timeline
    timeline = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
    for edge in timeline:
        # Check if we've already seen this post
        node = edge['node']
        id = node['id']
        if id in seen:
            print('Already seen:', id)
            continue

        # Found a new post
        logger.info('New post: {} ({})'.format(node['shortcode'], id))

        # Build full url
        post_url = 'https://www.instagram.com/p/{}/'.format(node['shortcode'])

        # Get attached media
        video_url = node.get('video_url')
        if video_url:
            fname = '/tmp/ig_media__{}.mp4'.format(datetime.utcnow().timestamp())
            download(video_url, fname)
            media_url = video_url
        else:
            image_url = node['display_url']
            fname = '/tmp/ig_media__{}.jpg'.format(datetime.utcnow().timestamp())
            download(image_url, fname)
            media_url = image_url

        # Get caption text
        caption = node['edge_media_to_caption']['edges'][0]['node']['text']

        logger.info('Post:', post_url)
        logger.info('Media:', fname)

        # Post to Facebook
        fb_api.put_object(
          parent_object=config.FB_PAGE_ID,
          connection_name="feed",
          message=caption,
          source=media_url,
          link=post_url
        )

        # Post to Twitter
        # <https://developer.twitter.com/en/docs/counting-characters>
        # Twitter character counting has a lot of idiosyncracies,
        # so use a smaller limit for safety
        max_len = 250
        short_url = shorten(post_url)
        short_url_len = max(23, len(short_url)) # urls considered 23 chars
        if len(caption) + len(short_url) + 1 > max_len:
            caption = caption[:(max_len - len(short_url) - 2)] + '…'
        caption = '{} {}'.format(caption, short_url)
        media = tw_api.media_upload(fname)
        tw_api.update_status(status=caption, media_ids=[media.media_id])

        seen.add(id)

    with open('seen.json', 'w') as f:
        json.dump(list(seen), f)


if __name__ == '__main__':
    main()

    scheduler = BlockingScheduler()
    scheduler.add_job(main, trigger='interval', minutes=config.UPDATE_INTERVAL)
    scheduler.start()
