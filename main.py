import requests as r
import datetime as dt
import time as t
import json

subreddit = "" # enter the name of the subreddit you want to scrape
time_back = 0 # enter the amount of days back you want to scrape

class reddit_post:
    def __init__(self, title, permalink, timestamp):
        self.title = title
        self.permalink = permalink
        self.timestamp = timestamp
        self.comments = []

    def __str__(self):
        return '{}, {} comments'.format(self.title[:40], len(self.comments))

    def extract_comments(self, children):
        results = []
        for item in children:
            data = item.get('data', {})
            if data.get('body'):
                results.append(data['body'])
            replies = data.get('replies')
            if isinstance(replies, dict):
                more_children = replies.get('data', {}).get('children', [])
                results.extend(self.extract_comments(more_children))
        return results
    
    def get_words(self, headers):
        t.sleep(1) # Be nice to Reddit's API
        comment_url = 'https://www.reddit.com{}.json'.format(self.permalink)
        try:
            response = r.get(comment_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 1 and 'data' in data[1]:
                    children = data[1]['data']['children']
                    self.comments = self.extract_comments(children)
                    return self.comments
                else:
                    return []
            else:
                print('error getting comments: {}'.format(response.status_code))
                return []   
        except r.exceptions.RequestException as e:
            print('error: {}'.format(e))
            return []
        except json.JSONDecodeError:
            print('failed to decode JSON from comment page:'.format(comment_url))
            return []


if __name__ == '__main__':
    base_url = 'https://www.reddit.com/r/{}/new.json'.format(subreddit)
    next_page_url = base_url
    amount_back = dt.datetime.now().timestamp() - (time_back * 86400)
    write_to = 'comments.json'
    headers = {
    'User-Agent': 'words getter'
    }
    crawling = True

    while crawling:
        post_data = []
        all_comments = []
        found_old_posts = False
        t.sleep(1)
        print('scraping comments from url: {}'.format(next_page_url))
        
        try:
            response = r.get(next_page_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'data' not in data or 'children' not in data['data']:
                    print('malformed response')
                    print(data)
                    break

                posts = data['data']['children']
                after_code = data['data']['after'] 
                
                if after_code:
                    next_page_url = '{}?after={}'.format(base_url, after_code)
                else:
                    next_page_url = None
                if not posts:
                    print('no posts found on this page')
                    break
                for post in posts:
                    current_post = post['data']
                    post_timestamp = current_post['created_utc']
                    if post_timestamp >= amount_back:
                        p = reddit_post(
                            current_post['title'],
                            current_post['permalink'],
                            current_post['created_utc']
                            )
                        post_data.append(p)
                    else:
                        found_old_posts = True
                        break
                
            else:
                print('error: {}'.format(response.status_code))
                print('{}'.format(response.text))
                break
                
        except r.exceptions.RequestException as e:
            print('connection error: {}'.format(e))
            break
        except json.JSONDecodeError:
            print('we have probably been rate limited')
            print('{}'.format(response.text))
            break
        except KeyError as e:
            print('Key error {}'.fprmat(e))
            print('{}'.format(data))
            break

        if post_data:
            print('extracting comments from {} posts'.format(len(post_data)))

            for i, post in enumerate(post_data):
                if i == len(post_data) - 1:
                    print('{}DONE'.format((i) * '*'))
                elif len(post_data) == 1:
                     print('...DONE')
                else:
                    print('{}{:02.0f}%{}'.format(i * '*', (i / (len(post_data) - 1)) * 100, (len(post_data) - i - 1) * '-'))
                comments = post.get_words(headers) 
                if comments:
                    all_comments.extend(comments)

            if all_comments:
                with open(write_to, 'a', encoding='utf-8') as f:
                    f.write('\n') 
                    json.dump(all_comments, f, indent = 4)
                
                print('{} new comments written to {}'.format(len(all_comments), write_to))
        else:
            print('no new post found within time limit, adjust amount back variable for more')

        if not next_page_url or found_old_posts:
            print('time limit reached')
            crawling = False
            break

        another_page = input('Would you like to scrape another page? (y/n) ').strip()
        if another_page.lower() != 'y':
            crawling = False
