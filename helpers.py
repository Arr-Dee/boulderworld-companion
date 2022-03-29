import re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import base64
from io import BytesIO
from os.path import exists

def plot_data(comp_id, score):

    # If there is no data available return
    if not exists(f'static/data/{comp_id}.csv'):
        return None

    # Read data in and sort by score
    df = pd.read_csv(f'static/data/{comp_id}.csv')
    df = df.sort_values(by=["Score"])

    # Set up fig and ax
    fig, ax = plt.subplots()

    # Convert scores from df to array
    x = df["Score"].to_numpy()

    # Set number of bins equal to number of rows/peoples
    n_bins = len(df.index)

    # Plot distribution
    n, bins, patches = ax.hist(x, n_bins, density=True, histtype='step',
                            cumulative=True)

    # Configure Plot
    if score is not None:
        plt.axvline(x=int(score), color='r', label=f'Your score - {score}')
        ax.legend(loc='right')
    ax.grid(True)
    ax.set_title('Cumulative distribution of total points scored')
    ax.set_xlabel('Points scored')
    ax.set_ylabel('Percentile')

    # Show plot (TESTING)
    #plt.show()

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")
    
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")

    return data


def calculate_score(data, zone, top):
    score = 0
    for climb in data:
        if climb == "top":
            score += top
        elif climb == "zone":
            score += zone

    return score


def password_check(password):
    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        8 characters length or more
        1 digit or more
        1 symbol or more
        1 uppercase letter or more
        1 lowercase letter or more
    """

    # calculating the length
    length_error = len(password) < 8

    # searching for digits
    digit_error = re.search(r"\d", password) is None

    # searching for uppercase
    uppercase_error = re.search(r"[A-Z]", password) is None

    # searching for lowercase
    lowercase_error = re.search(r"[a-z]", password) is None

    # searching for symbols
    #symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None

    # overall result
    password_ok = not ( length_error or digit_error or uppercase_error or lowercase_error)

    return {
        'password_ok' : password_ok,
        'length_error' : length_error,
        'digit_error' : digit_error,
        'uppercase_error' : uppercase_error,
        'lowercase_error' : lowercase_error,
        #'symbol_error' : symbol_error,
    }