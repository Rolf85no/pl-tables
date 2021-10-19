from flask import Flask, render_template, redirect,request,session
from flask_session import Session
from tempfile import mkdtemp
import pandas as pd
import numpy as np

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

SEASONS= ["9293.csv",
     "9394.csv", 
        "9495.csv", 
        "9596.csv", 
        "9697.csv",
        "9798.csv",
        "9899.csv",
        "9900.csv"]

def make_season(rounds, pl_season):
    goal_split = []
    season = pl_season

    # Reading data from csv
    data = pd.read_csv (f'csvfiles/{season}')
    df = pd.DataFrame(data, columns= ['Round', 'Team 1', 'Team 2', 'FT'])
    df_length = len(df)


    # Splitting the scores into two separate numbers in a list of lists
    for i in range (df_length):
        goal_split.append(df["FT"][i].split("-"))
        
    # Make panda of list
    df2 = pd.DataFrame(goal_split, columns = ['HG', 'AG'])
    df.drop('FT', inplace=True, axis=1)

    # Join the two pandas
    matches = pd.concat( [df, df2], axis=1, join="inner")

    # Make int of the split numbers, bacause the were strings
    matches['HG'] = matches['HG'].astype(int)
    matches['AG'] = matches['AG'].astype(int)

    # Set home win, away win or draw in pandas for each game
    conditions = [matches['HG'] > matches['AG'], 
                matches['HG'] < matches['AG']]
    choices = ['H', 'A']
    matches['HTR'] = np.select(conditions, choices, default='D')

    # Dette skjønner jeg ikke
    matches['H'] = matches['Team 1']
    matches['A'] = matches['Team 2']

    # Remove surplus rows
    cols_to_keep = ['Round', 'Team 1', 'Team 2', 'HG', 'AG', 'HTR']

    # Dette skjønner jeg ikke
    team_results = pd.melt(matches, 
    id_vars=cols_to_keep,
    value_vars=['H', 'A'],
    var_name='Home/Away',
    value_name='Team')

    team_results['Opponent'] = np.where(team_results['Team'] == team_results['Team 1'],
                                        team_results['Team 2'], team_results['Team 1'])

    points_map = {
        'W': 3,
        'D': 1,
        'L': 0
    }

    def get_result(score, score_opp):
        if score == score_opp:
            return 'D'
        elif score > score_opp:
            return 'W'
        
        else:
            return 'L'

    # Full time scores
    team_results['Goals'] = np.where(team_results['Team'] == team_results['Team 1'], team_results['HG'], team_results['AG'])
    team_results['Goals_Opp'] = np.where(team_results['Team'] != team_results['Team 1'], team_results['HG'], team_results['AG'])
    team_results['Result'] = np.vectorize(get_result)(team_results['Goals'], team_results['Goals_Opp'])
    team_results['Points'] = team_results['Result'].map(points_map)
    
    num_rounds = rounds

    if season == "9293.csv" or season == "9394.csv" or season == "9495.csv":
        pl_round = 22
    else:
        pl_round = 20
        if num_rounds > 38:
            num_rounds = 38

    cols_to_drop = ['Team 1', 'Team 2', 'HG', 'AG', 'HTR']

    team_results = (team_results.drop(cols_to_drop, axis=1).sort_values(by=['Round']).head(pl_round * num_rounds))

    def standings(frame, result_col, goals_col, goals_opp_col, points_col):
        """This function takes in a DataFrame and strings identifying fields
            to calculate the league table.
            
            Making it generalized will allow us to calculate league tables for
            First Half Goals only. Second Half Goals only.
            """

        record = {}

        record['Played'] = np.size(frame[result_col])
        record['Won'] = np.sum(frame[result_col] == 'W')
        record['Drawn'] = np.sum(frame[result_col] == 'D')
        record['Lost'] = np.sum(frame[result_col] == 'L')
        record['GF'] = np.sum(frame[goals_col])
        record['GA'] = np.sum(frame[goals_opp_col])
        record['GD'] = record['GF'] - record['GA']
        record['Points'] = np.sum(frame[points_col])

        return pd.Series(record,
                            index=['Played', 'Won', 'Drawn', 'Lost', 'GF', 'GA', 'GD', "Points"])


    results_byteam = team_results.groupby(['Team'])

    pl_table = results_byteam .apply(standings,
                result_col='Result',
                goals_col='Goals',
                goals_opp_col='Goals_Opp',
                points_col='Points').sort_values('Points', ascending=False)

    # Denne gjør at jeg fjerner antall kamper spilt
    pl_table.rename(columns={'Played': 'MP', 'Won': 'W', 'Drawn': 'D', 'Lost': 'L', 'Points': 'P'}, inplace=True)

    return pl_table

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Funker ikke enda
        maxRound = 38
        season= request.form.get("season")
        # Funker ikke enda
        if season == "9293.csv" or season == "9394.csv" or season == "9495.csv":
            maxRound = 42
        round_pl = int(request.form.get("round"))
        full_table = make_season(round_pl, season)
        return render_template("index.html", tables=[full_table.to_html(classes='data', header="true")], seasons=SEASONS, choose_season=season, choose_round=round_pl, maxRound=maxRound)

    else:
        season = "9293.csv" 
        round_pl = 42
        full_table = make_season(round_pl, season)
        return render_template("index.html", tables=[full_table.to_html(classes='data', header="true")], seasons=SEASONS, choose_season=season, choose_round=round_pl)

