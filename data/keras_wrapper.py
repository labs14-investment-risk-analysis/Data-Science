from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.wrappers.scikit_learn import KerasRegressor
from keras.preprocessing.sequence import TimeseriesGenerator
from sklearn.model_selection import train_test_split
from keras.models import Sequential
import warnings
import numpy as np
import os

import types


class KerasRegressorGenerator(KerasRegressor):
    """Use parameters: 'seq_length', 'batch_size', and 'epochs' in param_grid along with model parameters.
    Pass in validation data with parameter <val_data = {'X':X_val, 'y':y_val}> and
    <weights_dir = /path/to/some/folder>  directory in which to save weights data when calling fit.

        fit(X, y, val_data, weights_dir)

        Parameters:
            X: X_train data
            y: y_train data
            val_data: dictionary of validation datasets. Keys should be 'X' and 'y'
            weights_dir: Absolute path to directory where best weights will be saved
                * Weights will be saved as best_weights.<ticker_symbol>.hdf5
    """

    # This class can be improved by overriding the __init__ function. Research needed into Keras sklearn_wrapper
    # package to ensure all relevant variables are passed through, and generator data can be extracted on the fly
    # when and where needed.

    def fit(self, X, y, **kwargs):
        # taken from keras.wrappers.scikit_learn.KerasClassifier.fit ###################################################
        if self.build_fn is None:
            self.model = self.__call__(**self.filter_sk_params(self.__call__))
        elif not isinstance(self.build_fn, types.FunctionType) and not isinstance(self.build_fn, types.MethodType):
            self.model = self.build_fn(**self.filter_sk_params(self.build_fn.__call__))
        else:
            self.model = self.build_fn(**self.filter_sk_params(self.build_fn))

        loss_name = self.model.loss
        if hasattr(loss_name, '__name__'):
            loss_name = loss_name.__name__

        ################################################################################################################

        # Define class-wide to bypass X and y input on score function
        self.train_data_generator = self.create_gens(X, y, seq_length=self.sk_params['seq_length'],
                                                     batch_size=self.sk_params['batch_size'])
        if 'symbol' in kwargs:
            self.symbol = kwargs['symbol']
        else:
            self.symbol = str(X.columns[0].split('_')[0])
        if 'weights_dir' not in kwargs:
            current_dir = os.getcwd() + '/results/' + self.symbol + '/'
            try:
                os.stat(current_dir)
            except:
                os.mkdir(current_dir)
                warnings.warn('created directory at {}'.format(current_dir))
            file_path = ("{}/best_weights.{}.hdf5"
                         .format(current_dir, self.symbol))

        else:
            weights_dir = kwargs['weights_dir']
            file_path = ("{}/best_weights.hdf5"
                         .format(kwargs['weights_dir']))
            try:
                os.stat(weights_dir)
            except:
                os.mkdir(weights_dir)
                warnings.warn('created directory at {}'.format(weights_dir))

        # Make sure val_data is present. If absent, train without validation and warn.
        if 'val_data' in kwargs:

            self.val_data_generator = self.create_gens(kwargs['val_data']['X'],
                                                       kwargs['val_data']['y'],
                                                       seq_length=self.sk_params['seq_length'],
                                                       batch_size=self.sk_params['batch_size'])

            early_stopping = EarlyStopping(monitor='val_loss', patience=5, verbose=5, mode="min",
                                           # restore_best_weights=True                     # Enabling can cause errors!
                                           )                                               # Restore with .hdf5 for now.
            model_checkpoint = ModelCheckpoint(monitor='val_loss',
                                               filepath=file_path, verbose=5,
                                               save_best_only=True, mode="min")
        else:
            warnings.warn("Warning: Overfitting danger! Missing validation data, training without validation.")
            val_data_generator = None
            early_stopping = EarlyStopping(monitor="loss", patience=3, verbose=5, mode="min", restore_best_weights=True)
            model_checkpoint = ModelCheckpoint("results/best_weights.{epoch:02d}-{loss:.5f}.hdf5", monitor="loss",
                                               verbose=5, save_best_only=True, mode="min")

        callbacks = [early_stopping, model_checkpoint]

        epochs = self.sk_params['epochs'] if 'epochs' in self.sk_params else 100

        self.__history = self.model.fit_generator(
            self.train_data_generator,
            epochs=epochs,
            validation_data=self.val_data_generator,
            callbacks=callbacks,
            verbose=2
        )

        return self.__history

    def score(self, x, y, **kwargs):
        """Returns the mean loss on the given test data and labels.

        # Arguments
            Because of inheritance issues, score needs x and y passed
            in. They are not used. Gets data from the generator. This
            allows tuning of batch size and sequence length.
        # Returns
            score: float
                Mean accuracy of predictions on `x` wrt. `y`.
        """
        # Get keyword args applicable to Keras Sequential.evaluate_generator
        # from sk_params.
        kwargs = self.filter_sk_params(Sequential.evaluate_generator, kwargs)

        # Evaluate generator with tunable arguments. Returns loss specified in fit.
        loss = self.model.evaluate_generator(self.train_data_generator, **kwargs)

        # If statement, some loss functions return multiple scores.
        # Parent functions require loss as float, can't handle list.
        if isinstance(loss, list):
            return -loss[0]
        return -loss

    @property
    def history(self):
        # History getter function
        return self.__history

    def create_gens(self, X, y, seq_length=30, batch_size=15):

        # Create time series generator. Generator allows tuning of
        # parameters.
        generator = TimeseriesGenerator(X, y,
                                        length=seq_length,
                                        sampling_rate=1,
                                        stride=1,
                                        batch_size=batch_size)
        return generator
