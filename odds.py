import argparse
import requests
import os
import collections
import json
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
SPORT = 'basketball_nba'

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

odds_response = requests.get(f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds', params={
    'api_key': API_KEY,
    'regions': REGIONS,
    'markets': MARKETS,
    'oddsFormat': ODDS_FORMAT,
    'dateFormat': DATE_FORMAT,
})

if odds_response.status_code != 200:
    print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')

else:
    odds_json = odds_response.json()
    print('Number of events:', len(odds_json))
    # print(odds_json)

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

        odds_dict = collections.defaultdict(list)

        # fill odds_dict
        for bookmaker in event['bookmakers']:
            bookmaker_name = bookmaker['key']
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

            # print to console
            print('{} (underdog) vs {} (favorite) '.format(underdog_max_odd_entity['underdog']['name'], favorite_max_odd_entity['favorite']['name']))
            print('return %: {:.1f}%, return: {:.1f}, capital: {:.1f}'.format(return_percentage, val_return, capital))
            print('Bet Underdog from [{}]'.format(underdog_max_odd_bookmaker))
            print('Bet Favorite from [{}]'.format(favorite_max_odd_bookmaker))
            print('---------------------------------------------------------------------')











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