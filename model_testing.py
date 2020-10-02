import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#Get data
url = 'https://fantasy.premierleague.com/api/bootstrap-static/'

r = requests.get(url)

json = r.json()

elements_df = pd.DataFrame(json['elements'])

element_types_df = pd.DataFrame(json['element_types'])

teams_df = pd.DataFrame(json['teams'])

events_df = pd.DataFrame(json['events'])

gameweek = events_df[events_df['average_entry_score'] > 0]

actual_pts = elements_df[['web_name','event_points','bonus']]

prediction = pd.read_csv('pts_model_GW' + str(max(gameweek['id'])+1) + '.csv')

prediction['actual_pts'] = prediction.id.map(elements_df.set_index('id').event_points)
prediction['now_minutes'] = prediction.id.map(elements_df.set_index('id').minutes)
prediction['event_minutes'] = prediction.now_minutes - prediction.minutes
#prediction = prediction[prediction['event_minutes'] > 0]

prediction['error'] = prediction.xPts - prediction.actual_pts

MSE = (prediction.error * prediction.error).mean()

print(MSE)

groups = prediction.groupby('Position')

for group in groups:
    plt.plot(group.actual_pts,group.xPts)
    plt.show()



