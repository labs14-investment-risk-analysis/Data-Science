import random
import numpy as np
import pandas as pd
import os, sys
import pickle
import warnings

from fin_data import DailyTimeSeries
from fracdiff import FractionalDifferentiation as fd
from keras_wrapper import KerasRegressorGenerator

from time import sleep
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import LSTM
from keras.layers import Dense
from keras.layers import RepeatVector
from keras.layers import TimeDistributed
from keras.layers import Dropout
from keras import optimizers

random.seed(42)

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


pd.options.display.max_rows = 999
pd.options.display.max_columns = 999

warnings.simplefilter(action='ignore', category=FutureWarning)


class ModelMaker:

    def __init__(self,
                 symbol,
                 fundamentals=['totalrevenue', 'totalcostofrevenue', 'totalgrossprofit',
                               'totalpretaxincome', 'weightedavebasicdilutedsharesos', 'cashdividendspershare'],
                 technicals=['SMA', 'WMA', 'STOCH', 'ROC', 'AROON'],
                 macros=['housing_index', 'confidence_index', 'trade_index', 'longterm_rates', 'shortterm_rates'],
                 shift=1
                 ):
        self.symbol = symbol
        self.fundamentals = fundamentals
        self.technicals = technicals
        self.macros = macros
        self.shift = shift
        self.X_train = None
        self.X_test = None
        self.X_val = None
        self.X_cols = None
        self.y_train = None
        self.y_test = None
        self.y_val = None

    def create_model(self, seq_length,
                     batch_size,
                     epochs,
                     lstm_layers=[361, 196, 81, 64],
                     dropouts=[0.2, 0.2, 0.2, 0.2],
                     l_rate=0.015,
                     p=0.01,
                     decay=0.0001,
                     # optimizer,
                     loss='mean_squared_logarithmic_error'
                     ):

        model = Sequential()
        model.add(LSTM(lstm_layers[0],
                       activation='relu',
                       return_sequences=True,
                       input_shape=(seq_length, self.X_train.shape[1])))
        model.add(Dropout(dropouts[0]))
        for n_cells, drop in zip(lstm_layers[1:-1], dropouts[1:-1]):
            model.add(LSTM(n_cells, activation='relu',
                           recurrent_activation='selu',
                           return_sequences=True
                           ))
            model.add(Dropout(drop))
        model.add(LSTM(lstm_layers[-1], activation='selu'))
        model.add((Dropout(dropouts[-1])))
        model.add(Dense(1))

        sgd = optimizers.sgd(lr=l_rate, momentum=p, decay=decay)

        model.compile(optimizer=sgd, loss=loss, metrics=['accuracy'])

        return model

#    def set_params(self, lstm_layers, dropouts, l_rate, momentum, decay, loss):

    def fit_model(self, param_grid):
        self.get_data()
        krgmodel = KerasRegressorGenerator(build_fn=self.create_model)

        grid = GridSearchCV(estimator=krgmodel, param_grid=param_grid, n_jobs=-1)
        grid_results=grid.fit(self.X_train, self.y_train, val_data={'X':self.X_val, 'y':self.y_val})
        best = grid.best_estimator_
        return grid_results, best









    def get_data(self, train_cut=.8, frac_diff_target=True):

        dts = DailyTimeSeries(self.symbol)
        df = dts.initiate()
        sleep(5)

        df = dts.add_fundamentals(df, self.fundamentals)
        sleep(7)
        df = dts.add_technicals(self.technicals, df)
        sleep(15)
        df = dts.add_macro(df, self.macros)

        todrop = []

        for col in df.columns:
            if df[col].isnull().sum() / len(df) > .25:
                print('{} is missing '.format(col), df[col].isnull().sum())
                print('{} dropped'.format(col))
                todrop.append(col)

        df = df.drop(labels=todrop, axis=1)

        if frac_diff_target:
            if str(self.symbol + '_adjusted_close') in df.columns:
                df['target'] = (fd.frac_diff_ffd(df[[str(self.symbol + '_adjusted_close')]],
                                                 .35,
                                                 .001).shift(-self.shift)[str(self.symbol + '_adjusted_close')])
            else:
                df['target'] = (fd.frac_diff_ffd(df[[str(self.symbol + '_close')]],
                                                 .35,
                                                 .001).shift(-self.shift)[str(self.symbol + '_close')])
        else:
            if str(self.symbol + '_adjusted_close') in df.columns:
                df['target'] = df[str(self.symbol + '_adjusted_close')]
            else:
                df['target'] = df[str(self.symbol + '_close')]

        df = df.dropna(axis=0)

        print('nulls in target = ', df['target'].isnull().sum())
        df = df.fillna(value=0)

        X = df.drop(columns='target')
        y = df[['target']].values

        self.X_cols = X.columns

        scaler = MinMaxScaler()
        scaler.fit(X)

        X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                            train_size=train_cut,
                                                            shuffle=False)

        X_test, X_val, y_test, y_val = train_test_split(X_test, y_test,
                                                        train_size=.6,
                                                        shuffle=False)
        self.X_train = scaler.transform(X_train)
        self.X_test = scaler.transform(X_test)
        self.X_val = scaler.transform(X_val)
        self.y_train = y_train
        self.y_test = y_test
        self.y_val = y_val

        return None