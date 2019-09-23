#import sys

#sys.path.insert(0, '/home/joe/Documents/LambdaSchool/labs_ir/repos/Data-Science/data')

from keras.preprocessing.sequence import TimeseriesGenerator
from fin_data import DailyTimeSeries
from time import sleep
from fracdiff import FractionalDifferentiation as fd

from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

import numpy as np
import pandas as pd
#import os

class Data:

    def __init__(self,
                 symbol,
                 fundamentals,
                 technicals,
                 macros,
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

    def create_gens(self, seq_length=30, batch_size=15):
        train_data_generator = TimeseriesGenerator(self.X_train, self.y_train,
                                                   length=seq_length,
                                                   sampling_rate=1,
                                                   stride=1,
                                                   batch_size=batch_size)

        test_data_generator = TimeseriesGenerator(self.X_test, self.y_test,
                                                  length=seq_length,
                                                  sampling_rate=1,
                                                  stride=1,
                                                  batch_size=batch_size)

        val_data_generator = TimeseriesGenerator(self.X_val, self.y_val,
                                                 length=seq_length,
                                                 sampling_rate=1,
                                                 stride=1,
                                                 batch_size=batch_size)

        return train_data_generator, test_data_generator, val_data_generator

    def extract_data(self, generator):
        for i in np.arange(len(generator)):
            if i == 0:
                a, b = generator[i]
            else:
                c, d = generator[i]

                a = np.vstack((a, c))
                b = np.vstack((b, d))

        return a, b