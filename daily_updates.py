# coding: utf-8

from datetime import datetime, timezone, timedelta
import json
import time
from urllib import request


# sourced from https://www.datasciencelearner.com/how-to-get-json-data-from-url-in-python/
def getResponse(url):
    operUrl = request.urlopen(url)
    if(operUrl.getcode() == 200):
        data = operUrl.read()
        jsonData = json.loads(data.decode('utf-8'))
    else:
        print("Error receiving data", operUrl.getcode())
    return jsonData


FANTASY_TEAMS_covid_year_2021 = {
    'Fish': [6, 23, 21, 25],  # Bruins, Canucks, Avs, Stars
    'Kenny': [18, 10, 19, 4],  # Preds, Leafs, Blues, Flyers
    'Brett': [16, 20, 54, 15],  # Hawks, Flames, Knights, Caps
    'Td': [3, 14, 52, 30]  # Rags, Lightning, Jets, Wild
}
FANTASY_TEAMS = {
    'Fish': [6, 15, 55, 52],  # Bruins, Caps, Kraken, Jets
    'Kenny': [13, 12, 20, 18],  # Panthers, Canes, Flames, Preds
    'Brett': [14, 2, 22, 16],  # Lightning, Isles, Oilers, Hawks
    'Td': [10, 3, 54, 30]  # Leafs, Rags, Knights, Wild
}


def get_record(data, team_id):
    for division in range(4):
        for record in data['records'][division]['teamRecords']:
            if record['team']['id'] == team_id:
                return record
    return {}


def parse_zulu_time(zulu_time):
    t = datetime.strptime(zulu_time, "%Y-%m-%dT%H:%M:%SZ")
    t2 = t.replace(tzinfo=timezone.utc)
    is_dst = time.daylight and time.localtime().tm_isdst > 0
    utc_offset = time.altzone if is_dst else time.timezone
    t3 = t2.astimezone(tz=timezone(offset=-timedelta(seconds=utc_offset)))
    return "{}{} {}".format(t3.hour%12, ":{}".format(t3.minute) if t3.minute else "", "pm" if t3.hour >= 12 else "am")
    #return t3.strftime("%I:%M %p") if t3.minutes else "{} PM".format(24-t3.hours)


def optional_fantasy_roster_in_parens(team_id):
    for fteam, fids in FANTASY_TEAMS.items():
        if team_id in fids:
            return " [_{}_]".format(fteam)
    return ''


def get_recap_link(game_pk):
    url = "https://statsapi.web.nhl.com/api/v1/game/{}/content/".format(game_pk)
    data = getResponse(url)

    recap_data = next(obj_dict for obj_dict in data['media']['epg'] if obj_dict['title'] == 'Recap')
    recap_vid = get_vid_link(recap_data['items'][0])
    goal_vids = [get_vid_link(item, use_blurb=False) for item in sorted(data['highlights']['scoreboard']['items'], key=lambda i:  i['mediaPlaybackId'])]

    return "{}. Goals: {}".format(recap_vid, ", ".join(goal_vids))


def get_vid_link(data, use_blurb=True):
    possible_links = data['playbacks']
    url = next(data['url'] for data in possible_links if data['name'] == 'FLASH_1800K_896x504')
    return "<{}|{}>".format(url, data['blurb'] if use_blurb else data['title'].replace('\'', ' ').split()[0])

def get_yesterday_results():
    url = "https://statsapi.web.nhl.com/api/v1/schedule?date={}".format(
        (
            datetime.today()+timedelta(days=-1)
        ).strftime("%Y-%m-%d")
    )
    data = getResponse(url)
    if not data['dates']:
        return "ERROR: no games yesterday!\\n"

    ret = "*Yesterday's results:*\\n"


    for game in data['dates'][0]['games']:
        recap_link_if_avail = get_recap_link(game['gamePk'])
        team_away = game['teams']['away']
        team_home = game['teams']['home']
        winner = team_away if team_away['score'] > team_home['score'] else team_home
        loser = team_away if team_away['score'] < team_home['score'] else team_home
        ret += "- "
        ret += winner['team']['name'].split(' ')[-1]
        ret += optional_fantasy_roster_in_parens(winner['team']['id'])
        ret += " over "
        ret += loser['team']['name'].split(' ')[-1]
        ret += optional_fantasy_roster_in_parens(loser['team']['id'])
        if recap_link_if_avail:
            ret += ": {}".format(recap_link_if_avail)
        ret += "\\n"

    return ret


def get_todays_games():
    url = "https://statsapi.web.nhl.com/api/v1/schedule?date={}".format(datetime.today().strftime("%Y-%m-%d"))
    data = getResponse(url)

    if not data['dates']:
        return "ERROR: no games today!\\n"

    ret = "*Today's games:*\\n"


    for game in data['dates'][0]['games']:
        ret += "- "
        ret += game['teams']['away']['team']['name'].split(' ')[-1]
        ret += optional_fantasy_roster_in_parens(game['teams']['away']['team']['id'])
        ret += " @ "
        ret += game['teams']['home']['team']['name'].split(' ')[-1]
        ret += optional_fantasy_roster_in_parens(game['teams']['home']['team']['id'])
        ret += ", "
        ret += parse_zulu_time(game['gameDate'])
        ret += "\\n"

    return ret


def main():
    url = 'https://statsapi.web.nhl.com/api/v1/standings'
    data = getResponse(url)

    results = {}
    # from slack, midyear '22
    # Proposal: fish and Brett pick two teams each. 2 game points per goal your team scores
    # fish: atl/pac, brett: met/cen
    # met6-pac4, cen8-atl5, met5-cen3
    ALL_STAR_BONUS_PTS = {
        'Brett': 44,
        'Fish': 18
    }
    for fantasy_team, irl_team_ids_list in FANTASY_TEAMS.items():
        results[fantasy_team] = [ALL_STAR_BONUS_PTS.get(fantasy_team, 0), 0]
        for team_id in irl_team_ids_list:
            team_record = get_record(data, team_id)
            results[fantasy_team][0] += team_record['points']
            results[fantasy_team][1] += team_record['gamesPlayed']

    # this sorts by total points
    results = sorted(results.items(), key=lambda kv: (kv[1][0], kv[0]), reverse=True)

    ret = "*Daily Fantasy Update*\\n\\n"
    for result in results:
        ret += "`{0}: {1} pts, {2} gp; {3:.3f}`\\n".format(result[0].ljust(5), str(result[1][0]).rjust(3), str(result[1][1]).rjust(2), (0.5*result[1][0]/result[1][1]) if result[1][1] != 0 else 0.5)

    print(ret)
    print(get_yesterday_results())
    print(get_todays_games())


if __name__ == "__main__":
    main()
