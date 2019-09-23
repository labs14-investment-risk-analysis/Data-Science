#import sys

#sys.path.insert(0, '/home/joe/Documents/LambdaSchool/labs_ir/repos/Data-Science/data')

from data_retrieval import Data

import random
import numpy as np
import pandas as pd
import os, sys
import matplotlib.pyplot as plt

from sklearn.preprocessing import MinMaxScaler

from keras.models import Sequential
from keras.layers import LSTM
from keras.layers import Dense
from keras.layers import RepeatVector
from keras.layers import TimeDistributed
from keras.layers import Dropout
from keras import optimizers

from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

from keras.preprocessing.sequence import TimeseriesGenerator
from keras.callbacks import ModelCheckpoint, EarlyStopping


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

import pickle
import warnings

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
        self.X_cols = None

    def create_model(self, lstm_layers=[361, 196, 81, 64],
                     dropouts=[0.2, 0.2, 0.2, 0.2],
                     l_rate=0.015,
                     p=0.01,
                     decay=0.0001,
                     # optimizer,
                     loss='mean_squared_logarithmic_error'):

        model = Sequential()
        for n_cells, drop in zip(lstm_layers, dropouts):
            model.add(LSTM(n_cells, activation='relu', recurrent_activation='selu'))
            model.add(Dropout(drop))
        model.add(Dense(1))

        sgd = optimizers.sgd(lr=l_rate, momentum=p, decay=decay)

        model.compile(optimizer=sgd, loss=loss)

        return model

#    def set_params(self, lstm_layers, dropouts, l_rate, momentum, decay, loss):

    def fit_model(self, n_epochs, seq_lengths, batch_sizes):
        dg = Data(self.symbol, self.technicals, self.macros, shift=1)
        dg.get_data()

        for i in range(n_epochs):
            train_data_generator, test_data_generator, val_data_generator = dg.create_gens(random.choice)