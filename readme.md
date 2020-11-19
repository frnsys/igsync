Scrapes an Instagram page and mirrors those posts on Facebook and Twitter.

Requires:

- bit.ly, for url shortening
- Twitter: make sure the app is set to Read and Write access
- Facebook: make sure the `pages_manage_posts` permission is included

To get a permanent Facebook page access token:

```bash
APP_ID=<your app id>
APP_SECRET=<your app secret>

# Generated via the Graph API explorer
# make sure it has the correct permissions
# Make sure this is a "Page Access Token" not a "User Access Token"
PAGE_ACCESS_TOKEN=<your short-lived page access token>

RESP=$(curl "https://graph.facebook.com/v2.10/oauth/access_token?grant_type=fb_exchange_token&client_id=$APP_ID&client_secret=$APP_SECRET&fb_exchange_token=$PAGE_ACCESS_TOKEN")
SHORT_ACCESS_TOKEN=$(echo $RESP | jq -r .access_token)
RESP=$(curl https://graph.facebook.com/v2.10/me?access_token=$SHORT_ACCESS_TOKEN)
PAGE_ID=$(echo $RESP | jq -r .id)
curl "https://graph.facebook.com/v2.10/$PAGE_ID?fields=access_token&access_token=$SHORT_ACCESS_TOKEN"
```

In `config.py`:

```python
UPDATE_INTERVAL = 60*5

IG_URL = '<url of instagram account to scrape>'

FB_PAGE_ID = '<facebook page id>'
FB_ACCESS_TOKEN = '<facebook permanent page access token, see above>'

TW_CONSUMER_KEY = '<twitter consumer key>'
TW_CONSUMER_SECRET = '<twitter consumer secret>'
TW_ACCESS_TOKEN = '<twitter access token>'
TW_ACCESS_TOKEN_SECRET = '<twitter access token secret>'

BITLY_ACCESS_TOKEN = '<bitly access token>'
```
