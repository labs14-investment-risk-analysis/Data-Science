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
from keras.preprocessing.sequence import TimeseriesGenerator
from keras.models import Sequential
from keras.layers import LSTM
from keras.layers import Dense
from keras.layers import RepeatVector
from keras.layers import TimeDistributed
from keras.layers import Dropout
from keras import optimizers
from shap import DeepExplainer

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
                 save_path,
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
        self.save_path = save_path + '/' + self.symbol + '/'
        self.X_train = None
        self.X_test = None
        self.X_val = None
        self.X_cols = None
        self.y_train = None
        self.y_test = None
        self.y_val = None
        self.best_model = None
        self.shapley_full = None

        try:
            os.stat(save_path)
        except:
            os.mkdir(save_path)

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
                           #recurrent_activation='relu',
                           return_sequences=True
                           ))
            model.add(Dropout(drop))
        model.add(LSTM(lstm_layers[-1], activation='relu'))
        model.add((Dropout(dropouts[-1])))
        model.add(Dense(1))

        sgd = optimizers.sgd(lr=l_rate, momentum=p, decay=decay)

        model.compile(optimizer=sgd, loss=loss)

        return model

    def fit_model(self, param_grid):
        # Parameter grid for create_model, save_path and symbol
        self.get_data()
        krg_model = KerasRegressorGenerator(build_fn=self.create_model)

        grid = GridSearchCV(estimator=krg_model, param_grid=param_grid, n_jobs=-1)
        grid_results = grid.fit(self.X_train,
                                self.y_train,
                                val_data={'X': self.X_val, 'y': self.y_val},
                                weights_dir=self.save_path,
                                symbol=self.symbol)
        best = grid_results.best_estimator_
        return grid_results, best

    def save_results(self, sk_results, sk_estimator):
        # Pass in 'best' from fit_model return
        save_params_name = "params.{}.pickle".format(self.symbol)
        save_model_name = "model.{}".format(self.symbol)
        save_shapley_name = "shapley.{}".format(self.symbol)
        try:
            params_file = open(str(self.save_path + save_params_name), 'wb')
            pickle.dump(sk_results.best_params_, params_file)
            params_file.close()
            print('saved params as ', save_params_name)
            sk_estimator.model.save(str(self.save_path + save_model_name))
            print('saved model as ', save_model_name)
            np.save(str(self.save_path + save_shapley_name), self.shapley_full)
            print('saved shapley values as ', save_shapley_name)
        except:
            print('error saving files')
        return None


    def extract_data(self, generator):

        #
        for i in np.arange(len(generator)):
            if i == 0:
                a, b = generator[i]
            else:
                c, d = generator[i]

                a = np.vstack((a, c))
                b = np.vstack((b, d))

        return a, b

    def get_data(self, train_cut=.8, frac_diff_target=True):

        dts = DailyTimeSeries(self.symbol)
        df = dts.initiate()
        sleep(3)

        df = dts.add_fundamentals(df, self.fundamentals)
        sleep(5)
        df = dts.add_technicals(self.technicals, df)
        sleep(10)
        df = dts.add_macro(df, self.macros)

        to_drop = []

        for col in df.columns:
            if df[col].isnull().sum() / len(df) > .25:
                print('{} is missing '.format(col), df[col].isnull().sum())
                print('{} dropped'.format(col))
                to_drop.append(col)

        df = df.drop(labels=to_drop, axis=1)

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

    def create_gens(self, X, y, seq_length=30, batch_size=15):
        generator = TimeseriesGenerator(X, y,
                                        length=seq_length,
                                        sampling_rate=1,
                                        stride=1,
                                        batch_size=batch_size)
        return generator

    def get_shapley(self, best):
        self.best_model = best
        dexp = DeepExplainer(model=self.best_model)
        best_params = self.best_model.best_prams_
        seq_length = best_params['seq_length']
        batch_size = best_params['batch_size']
        data = self.create_gens(X = self.X_test,
                                y = self.y_test,
                                seq_length=seq_length,
                                batch_size=batch_size)
        X_test_processed, y_test_processed = self.extract_data(data)
        dexp = DeepExplainer(model=self.best_model, data=X_test_processed)
        self.shapley_full = dexp.shap_values(X_test_processed)
        return None

