import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson


#Get data
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'

r = requests.get(url)

json = r.json()

elements_df = pd.DataFrame(json['elements'])

element_types_df = pd.DataFrame(json['element_types'])

teams_df = pd.DataFrame(json['teams'])

events_df = pd.DataFrame(json['events'])


#Most owned
print(elements_df.columns)

ownership = elements_df[['web_name','selected_by_percent']]

ownership['selected_by_percent'] = ownership.selected_by_percent


#Ownership changes
df = elements_df[['web_name','transfers_in_event','transfers_out_event','selected_by_percent']]

df['transfers'] = df.transfers_in_event - df.transfers_out_event

print(df.sort_values('transfers',ascending=False).head(10))
print(df.sort_values('transfers',ascending=True).head(10))


#Price changes
df = elements_df[['web_name','now_cost','cost_change_start','cost_change_event']]

print(df.sort_values('cost_change_start',ascending=False).head(10))
print(df.sort_values('cost_change_start',ascending=True).head(10))


#Undervalued and Overvalued players
df = elements_df[['web_name', 'value_season']]

df['value_season'] = pd.to_numeric(df.value_season)

avg_value = df.value_season.mean()

df['value_index'] = df.value_season/avg_value

df = df[df['value_season'] != 0]

print(df.sort_values('value_index', ascending=False).head(10))
print(df.sort_values('value_index', ascending=True).head(10))


#Where are the points coming from!
df = elements_df[elements_df['minutes'] > 0]
df = df[['element_type','points_per_game']]
df['points_per_game'] = pd.to_numeric(df.points_per_game)
print(df.groupby('element_type').mean())


