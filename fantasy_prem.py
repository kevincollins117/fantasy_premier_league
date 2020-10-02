import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import date




#Get data
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'

r = requests.get(url)

json = r.json()

elements_df = pd.DataFrame(json['elements'])

element_types_df = pd.DataFrame(json['element_types'])

teams_df = pd.DataFrame(json['teams'])

events_df = pd.DataFrame(json['events'])

print(elements_df.columns)


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

#Expected points for yellows
def yellows_pts(players):
    avg_yellows = players['yellow_cards']/players['games_played']
    return avg_yellows*(-1)

#Points for saves
def saves_pts(players):
    avg_saves = players['saves']/players['games_played']
    return avg_saves*(1/3)



#Totalling points function
def xPts(players):
    return np.where(players['element_type']==4,
            players['xG']*4 + players['xA']*3 + minutes_pts(players) + yellows_pts(players),
            np.where(players['element_type']==3,
                players['xG']*5 + players['xA']*3 + poisson.pmf(0,players['xGA'])*1 + minutes_pts(players) + yellows_pts(players),
                    np.where(players['element_type']==2,
                        players.xG*6 + players.xA*3 + poisson.pmf(0,players.xGA)*4 + (poisson.cdf(4,players.xGA)-poisson.cdf(2,players.xGA))*(-2) + (1-poisson.cdf(4,players.xGA))*(-2) + minutes_pts(players) + yellows_pts(players),
                        np.where(players['element_type']==1,
                            poisson.pmf(0,players.xGA)*4 + (poisson.cdf(4,players.xGA)-poisson.cdf(2,players.xGA))*(-2) + (1-poisson.cdf(4,players.xGA))*(-2) + minutes_pts(players) + yellows_pts(players) + saves_pts(players),
                            0))))

                        



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
elements_df['avg_GA'] = elements_df.team.map(goals_conceded_df.avg_ga)


fixture_df = get_fixtures(elements_df)

elements_df['next_fixture'] = elements_df.id.map(fixture_df.set_index('id').next_fixture)

elements_df['opponent_GA'] = elements_df.next_fixture.map(goals_conceded_df.avg_ga)
elements_df['opponent_GF'] = elements_df.next_fixture.map(team_goals_df.avg_gf)


elements_df['goal_contr'] = elements_df['goals_scored']/elements_df['team_goals']
elements_df['asst_contr'] = elements_df['assists']/elements_df['team_goals']

elements_df['xGF'] = elements_df.opponent_GA*elements_df.avg_GF/avg_goals_per_game
elements_df['xGA'] = elements_df.opponent_GF*elements_df.avg_GA/avg_goals_per_game

elements_df['xG'] = elements_df.goal_contr*elements_df.xGF
elements_df['xA'] = elements_df.asst_contr*elements_df.xGF

elements_df['xPts'] = xPts(elements_df)

output = elements_df[['id', 'web_name','element_type','minutes','team','next_fixture','now_cost','xGF', 'xGA', 'xG', 'xA', 'xPts']]

output['Team'] = output.team.map(teams_df.set_index('id').name)
output['Opponent'] = output.next_fixture.map(teams_df.set_index('id').name)
output['Position'] = output.element_type.map(element_types_df.set_index('id').singular_name)

output = output[['id', 'web_name','minutes', 'Position', 'Team', 'Opponent', 'now_cost', 'xGF', 'xGA', 'xG', 'xA', 'xPts']]

gameweek = max(events_df[events_df['average_entry_score']>0]['id']) + 1

output['Gameweek'] = gameweek

print(output)

file_name = 'pts_model_GW' + str(gameweek) + '.csv'

output.to_csv(file_name)
