from decouple import config
from fin_data_fundamentals import find_fundamentals
from fin_data import DailyTimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.techindicators import TechIndicators
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import numpy as np
import quandl
import datetime
import warnings

def financials_available(symbol):
    alpha_vantage_key = config('ALPHA_VANTAGE')
    ts = TimeSeries(key=self.alpha_vantage_key,
                        output_format='pandas')

    data, meta_data = ts.get_daily_adjusted(symbol=symbol, outputsize='compact')

    data = data.drop(columns='8. split coefficient')

    return(data.columns)

def technicals_available(symbol):
    indicators = np.load('technicals_list.npy')
    have_techs = []
    ti = TechIndicators(key=alpha_vantage_key, output_format='pandas')
    for ind in indicators:
        try:
            got_techs = getattr(ti, ind)(symbol=symbol)
        except:
            continu
        if got_techs[0].isnull().sum().values[0] == 0:
            have_techs.append(got_techs[1]['2: Indicator'])

    return(have_techs)

def macros_available(symbol):
    macros = ['housing_index', 'confidence_index', 'trade_index', 'longterm_rates', 'shortterm_rates']
    dts = DailyTimeSeries(symbol)
    df = dts.initiate()
    df = dts.add_macro(df, macros)

    macro_na = []

    for ma in df.columns:


