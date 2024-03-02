import argparse
import requests
import os
import collections
import json
import base64
from email.message import EmailMessage
import google.auth
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

api_key_in_env = os.getenv("api_key")

# Obtain the api key that was passed in from the command line
parser = argparse.ArgumentParser(description='Sample V4')
parser.add_argument('--api-key', type=str, default='')
args = parser.parse_args()

# An api key is emailed to you when you sign up to a plan
# Get a free API key at https://api.the-odds-api.com/
API_KEY = args.api_key or api_key_in_env

# Sport key
# Find sport keys from the /sports endpoint below, or from https://the-odds-api.com/sports-odds-data/sports-apis.html
# Alternatively use 'upcoming' to see the next 8 games across all sports
SPORTS = [
    'basketball_nba',
    'americanfootball_nfl',
    'baseball_mlb',
    'icehockey_nhl'
]
# Bookmaker regions
# uk | us | us2 | eu | au. Multiple can be specified if comma delimited.
# More info at https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
REGIONS = 'us'

# Odds markets
# h2h | spreads | totals. Multiple can be specified if comma delimited
# More info at https://the-odds-api.com/sports-odds-data/betting-markets.html
# Note only featured markets (h2h, spreads, totals) are available with the odds endpoint.
MARKETS = 'h2h'

# Odds format
# decimal | american
ODDS_FORMAT = 'american'

# Date format
# iso | unix
DATE_FORMAT = 'iso'

available_bookmakers = {
    'draftkings',
    'fanduel',
    'wynnbet',
    'betrivers',
    'betmgm',
    'pointsbetus',
    'williamhill_us'
}

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
# First get a list of in-season sports
#   The sport 'key' from the response can be used to get odds in the next request
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

# sports_response = requests.get('https://api.the-odds-api.com/v4/sports', params={
#     'api_key': API_KEY
# })


# if sports_response.status_code != 200:
#     print(f'Failed to get sports: status_code {sports_response.status_code}, response body {sports_response.text}')

# else:
#     print('List of in season sports:', sports_response.json())



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
# Now get a list of live & upcoming games for the sport you want, along with odds for different bookmakers
# This will deduct from the usage quota
# The usage quota cost = [number of markets specified] x [number of regions specified]
# For examples of usage quota costs, see https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
email_content = []

for SPORT in SPORTS:
    odds_response = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds', params={
        'api_key': API_KEY,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': ODDS_FORMAT,
        'dateFormat': DATE_FORMAT,
    })

    if odds_response.status_code != 200:
        print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')
        exit()

    else:
        odds_json = odds_response.json()
        print('Number of events:', len(odds_json))

        # Check the usage quota
        print('Remaining requests', odds_response.headers['x-requests-remaining'])
        print('Used requests', odds_response.headers['x-requests-used'])

        print('---------------------------------------------------------------------')

        
        # Calculate arbitrage
        for event in odds_json:
            print('---------------------------------------------------------------------')
            print('** {} - {} vs {} **'.format(event['sport_title'], event['home_team'], event['away_team']))
            print('---------------------------------------------------------------------')
            print('---------------------------------------------------------------------')

            arbitrage_found = False
            email_content.append('** {} - {} vs {} **'.format(event['sport_title'], event['home_team'], event['away_team']))

            odds_dict = collections.defaultdict(list)

            # fill odds_dict
            for bookmaker in event['bookmakers']:
                bookmaker_name = bookmaker['key']
                if bookmaker_name not in available_bookmakers:
                    continue
                for market in bookmaker['markets']:
                    if market['key'] != 'h2h':
                        continue
                    outcomes = market['outcomes']
                    if outcomes[0]['price'] < 0 and outcomes[1]['price'] < 0:
                        # both odds negative. ignore this bet.
                        pass 
                    if outcomes[0]['price'] > 0 and outcomes[1]['price'] > 0:
                        # both odds positive. ignore this bet.
                        # TODO: is this a possible scenario?
                        pass 
                    elif outcomes[0]['price'] > 0:
                        # first team has positive odd (first team = underdog, second team = favorite)
                        odds_dict[outcomes[0]['name']].append({'bookmaker': bookmaker_name, 'underdog': outcomes[0], 'favorite': outcomes[1]})
                    else:
                        # second team has positive odd (first team = favorite, second team = underdog)
                        odds_dict[outcomes[1]['name']].append({'bookmaker': bookmaker_name, 'underdog': outcomes[1], 'favorite': outcomes[0]})

            # calculate max underdog odd and max favorite odd (max = most positive)
            for team_name in [event['home_team'], event['away_team']]:
                odds_list = odds_dict[team_name]
                if not odds_list:
                    continue
                underdog_max_odd_entity = max(odds_list, key=lambda x: x['underdog']['price'])
                underdog_max_odd = underdog_max_odd_entity['underdog']['price']
                underdog_max_odd_bookmaker = underdog_max_odd_entity['bookmaker']
                favorite_max_odd_entity = max(odds_list, key=lambda x: x['favorite']['price'])
                favorite_max_odd = favorite_max_odd_entity['favorite']['price']
                favorite_max_odd_bookmaker = favorite_max_odd_entity['bookmaker']

                # Tommy's Calculation according to Excel
                val_return = favorite_max_odd + (underdog_max_odd * ((100-favorite_max_odd)/(100+underdog_max_odd)))
                capital = underdog_max_odd * ((100-favorite_max_odd) / (underdog_max_odd + 100)) - favorite_max_odd
                return_percentage = 100 * val_return / capital

                # ignore negative returns
                if return_percentage <= 0:
                    continue
                
                # append to email content
                email_content.append('{} (underdog) vs {} (favorite) '.format(underdog_max_odd_entity['underdog']['name'], favorite_max_odd_entity['favorite']['name']))
                email_content.append('return %: {:.1f}%, return: {:.1f}, capital: {:.1f}'.format(return_percentage, val_return, capital))
                email_content.append('Bet Underdog from [{}]'.format(underdog_max_odd_bookmaker))
                email_content.append('Bet Favorite from [{}]'.format(favorite_max_odd_bookmaker))
                email_content.append('---------------------------------------------------------------------')
            
                arbitrage_found = True

                # print to console
                print('{} (underdog) vs {} (favorite) '.format(underdog_max_odd_entity['underdog']['name'], favorite_max_odd_entity['favorite']['name']))
                print('return %: {:.1f}%, return: {:.1f}, capital: {:.1f}'.format(return_percentage, val_return, capital))
                print('Bet Underdog from [{}]'.format(underdog_max_odd_bookmaker))
                print('Bet Favorite from [{}]'.format(favorite_max_odd_bookmaker))
                print('---------------------------------------------------------------------')

            if not arbitrage_found:
                email_content.pop()


def gmail_send_message():
  """Create and send an email message
  Print the returned  message id
  Returns: Message object, including message id

  Load pre-authorized user credentials from the environment.
  TODO(developer) - See https://developers.google.com/identity
  for guides on implementing OAuth2 for the application.
  """
# #   creds, _ = google.auth.load_credentials_from_file("samples-python/token.json")
#   creds, _ = google.auth.default()

  SCOPES = ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/gmail.modify"]

  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "C:\GithubProjects\sports-arbitrage\samples-python\credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("gmail", "v1", credentials=creds)
    message = EmailMessage()
    
    if email_content:
        message.set_content('\n'.join(email_content))
    else:
       print('No Arbitrage Found')
       exit(0)
        # message.set_content('No Arbitrage Found')

    message["To"] = "seunghunjang956@gmail.com;tomcho0515@gmail.com;jihoonyangg@gmail.com"
    message["From"] = "seunghunjang956@gmail.com"
    message["Subject"] = "Sports Arbitrage Notification"

    # encoded message
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    create_message = {"raw": encoded_message}
    # pylint: disable=E1101
    send_message = (
        service.users()
        .messages()
        .send(userId="me", body=create_message)
        .execute()
    )
    print(f'Message Id: {send_message["id"]}')
  except HttpError as error:
    print(f"An error occurred: {error}")
    send_message = None
  return send_message


gmail_send_message()



    # Sample Sports Odd Get Response Schema        
    # [
    #   {
    #     "id": "e912304de2b2ce35b473ce2ecd3d1502",
    #     "sport_key": "americanfootball_nfl",
    #     "sport_title": "NFL",
    #     "commence_time": "2023-10-11T23:10:00Z",
    #     "home_team": "Houston Texans",
    #     "away_team": "Kansas City Chiefs",
    #     "bookmakers": [
    #       {
    #         "key": "draftkings",
    #         "title": "DraftKings",
    #         "last_update": "2023-10-10T12:10:29Z",
    #         "markets": [
    #           {
    #             "key": "h2h",
    #             "last_update": "2023-10-10T12:10:29Z",
    #             "outcomes": [
    #               {
    #                 "name": "Houston Texans",
    #                 "price": 2.23
    #               },
    #               {
    #                 "name": "Kansas City Chiefs",
    #                 "price": 1.45
    #               }
    #             ]
    #           }
    #         ]
    #       }
    #     ]
    #   }
    # ]