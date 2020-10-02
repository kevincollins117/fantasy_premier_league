import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson




####Ideas: -rewrite to calculate statistics for ALL players at once
####       -write points() function that determines points for each type of player
####       -output summary: Name, Team Name, Opponenet Name, position, now_cost, xPts
####       -write script to compare predictions to actual (maybe save dynamic filenames)


#Get data
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'

r = requests.get(url)

json = r.json()

elements_df = pd.DataFrame(json['elements'])

element_types_df = pd.DataFrame(json['element_types'])

teams_df = pd.DataFrame(json['teams'])

events_df = pd.DataFrame(json['events'])


#Getting fixture data for individual players
def get_fixtures(players):
    fixture_rows = []
    
    for player in players['id']:
        player_id = player
    
        player_url = 'https://fantasy.premierleague.com/api/element-summary/' + str(player_id) + '/'
    
        r = requests.get(player_url)

        json = r.json()

        fixtures = pd.DataFrame(json['fixtures'])

        fixtures['opponent'] = np.where(fixtures.is_home==True, fixtures.team_a, fixtures.team_h)
    
        next_fixture = fixtures.iloc[0]['opponent']

        fixture_rows.append([player_id, next_fixture])

    fixture_df = pd.DataFrame(fixture_rows, columns = ['id','next_fixture'])

    return fixture_df

#Expected points for minutes
def minutes_pts(players):
    avg_minutes = players['minutes']/players['games_played']
    return (avg_minutes >= 70)*1 + (avg_minutes >= 45)*1


#Filter out players who have not played
elements_df = elements_df[elements_df['minutes'] > 0]

#Games played
keeper_index = elements_df['element_type']==1
keepers = elements_df[keeper_index]

games_played = keepers[['team','minutes']]

games_played = games_played.groupby('team').sum()/90


#Average goals scored per team
team_goals = elements_df[['team','goals_scored']]

team_goals_df = team_goals.groupby('team').sum()

team_goals_df['team'] = team_goals_df.index

team_goals_df['games_played'] = team_goals_df.team.map(games_played.minutes)

team_goals_df['avg_gf'] = team_goals_df.goals_scored/team_goals_df.games_played


#Average goals conceded per team

goals_conceded_df = keepers[['team','goals_conceded']]

goals_conceded_df = goals_conceded_df.groupby('team').sum()

goals_conceded_df['team'] = goals_conceded_df.index

goals_conceded_df['games_played'] = goals_conceded_df.team.map(games_played.minutes)

goals_conceded_df['avg_ga'] = goals_conceded_df.goals_conceded/goals_conceded_df.games_played


#####FIX ISSUE with overcounting goals

avg_goals_per_game = team_goals_df.goals_scored.sum()/team_goals_df.games_played.sum()


####Mapping important statistics
elements_df['games_played'] = elements_df.team.map(games_played.minutes)

elements_df['team_goals'] = elements_df.team.map(team_goals_df.goals_scored)
elements_df['avg_GF'] = elements_df.team.map(team_goals_df.avg_gf)



####Forwards
fwd_index = elements_df['element_type'] == 4
fwds = elements_df.loc[elements_df['element_type'] == 4]
fwds = fwds[['web_name', 'id', 'team', 'minutes', 'value_season', 'goals_scored', 'now_cost', 'assists']]

fwds['games_played'] = fwds.team.map(games_played.minutes)

fwds['team_goals'] = fwds.team.map(team_goals_df.goals_scored)
fwds['avg_GF'] = fwds.team.map(team_goals_df.avg_gf)


fixture_df = get_fixtures(fwds)

fwds['next_fixture'] = fwds.id.map(fixture_df.set_index('id').next_fixture)

fwds['goal_contr'] = fwds['goals_scored']/fwds['team_goals']
fwds['asst_contr'] = fwds['assists']/fwds['team_goals']

fwds['opponent_GA'] = fwds.next_fixture.map(goals_conceded_df.avg_ga)

fwds['xGF'] = fwds.opponent_GA*fwds.avg_GF/avg_goals_per_game

fwds['xG'] = fwds.goal_contr*fwds.xGF
fwds['xA'] = fwds.asst_contr*fwds.xGF

#Minutes (might need updating lol this was a big assumption)
fwds['avg_minutes'] = fwds.minutes/fwds.games_played
fwds['minutes_pts'] = minutes_pts(fwds)

fwds['xPts'] = fwds.xG*4 + fwds.xA*3 + fwds.minutes_pts
fwds['xValue'] = fwds.xPts/fwds.now_cost

fwd_stats = fwds[['web_name','xG','xA', 'xPts', 'xValue']]

print(fwd_stats.sort_values('xPts', ascending=False))

fwds.to_csv('fwds.csv')


####Midfielders
mids = elements_df.loc[elements_df['element_type']==3]
mids = mids[['web_name', 'id', 'team', 'minutes', 'value_season', 'goals_scored', 'now_cost', 'assists']]

mids['team_goals'] = mids.team.map(team_goals_df.goals_scored)
mids['avg_GF'] = mids.team.map(team_goals_df.avg_gf)

fixture_df = get_fixtures(mids)

mids['next_fixture'] = mids.id.map(fixture_df.set_index('id').next_fixture)

mids['goal_contr'] = mids['goals_scored']/mids['team_goals']
mids['asst_contr'] = mids['assists']/mids['team_goals']

mids['opponent_GA'] = mids.next_fixture.map(goals_conceded_df.avg_ga)

mids['xGF'] = mids.opponent_GA*mids.avg_GF/avg_goals_per_game

mids['xG'] = mids.goal_contr*mids.xGF
mids['xA'] = mids.asst_contr*mids.xGF


#Have to incorporate goals scored as well as goals conceded for mids
mids['opponent_GF'] = mids.next_fixture.map(team_goals_df.avg_gf)
mids['avg_GA'] = mids.team.map(goals_conceded_df.avg_ga)

mids['xGA'] = mids.opponent_GF*mids.avg_GA/avg_goals_per_game

mids['clean_sheet_prob'] = poisson.pmf(0, mids.xGA)

mids['minutes_pts'] = minutes_pts(mids)

#Totalling points
mids['xPts'] = mids.xG*5 + mids.xA*3 + mids.clean_sheet_prob*1 + mids.minutes_pts
mids['xValue'] = mids.xPts/mids.now_cost

mid_stats = mids[['web_name','xG','xA', 'xPts', 'xValue']]

print(mid_stats.sort_values('xPts', ascending=False))

mids.to_csv('mids.csv')


####Defenders
defs = elements_df.loc[elements_df['element_type']==2]
defs = defs[['web_name', 'id', 'team', 'minutes', 'value_season', 'goals_scored', 'now_cost', 'assists']]

defs['team_goals'] = defs.team.map(team_goals_df.goals_scored)
defs['avg_GF'] = defs.team.map(team_goals_df.avg_gf)

fixture_df = get_fixtures(defs)

defs['next_fixture'] = defs.id.map(fixture_df.set_index('id').next_fixture)

defs['goal_contr'] = defs['goals_scored']/defs['team_goals']
defs['asst_contr'] = defs['assists']/defs['team_goals']

defs['opponent_GA'] = defs.next_fixture.map(goals_conceded_df.avg_ga)

defs['xGF'] = defs.opponent_GA*defs.avg_GF/avg_goals_per_game

defs['xG'] = defs.goal_contr*defs.xGF
defs['xA'] = defs.asst_contr*defs.xGF





defs['opponent_GF'] = defs.next_fixture.map(team_goals_df.avg_gf)
defs['avg_GA'] = defs.team.map(goals_conceded_df.avg_ga)

defs['xGA'] = defs.opponent_GF*defs.avg_GA/avg_goals_per_game

defs['minutes_pts'] = minutes_pts(defs)


#Totalling points
defs['xPts'] = defs.xG*6 + defs.xA*3 + poisson.pmf(0,defs.xGA)*4 + (poisson.cdf(4,defs.xGA)-poisson.cdf(2,defs.xGA))*(-2) + (1-poisson.cdf(4,defs.xGA))*(-2) + defs.minutes_pts
defs['xValue'] = defs.xPts/defs.now_cost

def_stats = defs[['web_name','xG','xA', 'xPts', 'xValue']]

print(def_stats.sort_values('xPts', ascending=False))

defs.to_csv('defs.csv')


####Keepers
keepers = keepers[['web_name', 'id', 'team', 'saves', 'penalties_saved', 'penalties_missed', 'now_cost']]

fixture_df = get_fixtures(keepers)


#Totalling points
keepers

