from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.wrappers.scikit_learn import KerasRegressor
from keras.preprocessing.sequence import TimeseriesGenerator
from sklearn.model_selection import train_test_split
from keras.models import Sequential
import numpy as np

import types


class KerasRegressorGenerator(KerasRegressor):
    """Use parameters: 'seq_length', 'batch_size', and 'epochs' in param_grid along with model parameters
    pass in validation data with 'val_data': {'X':X_val, 'y':y_val} """

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

        self.train_data_generator = self.create_gens(X, y, seq_length=self.sk_params['seq_length'],
                                                batch_size=self.sk_params['batch_size'])
        self.symbol = kwargs['symbol']
        file_path = "/home/ec2-user/SageMaker/Data-Science/jupyter_notebooks/modeling/results/best_weights.{}.hdf5".format(self.symbol)
        if 'val_data' in kwargs:

            self.val_data_generator = self.create_gens(kwargs['val_data']['X'],
                                                  kwargs['val_data']['y'],
                                                  seq_length=self.sk_params['seq_length'],
                                                  batch_size=self.sk_params['batch_size'])

            early_stopping = EarlyStopping(monitor='val_loss', patience=5, verbose=5, mode="min",
                                           #restore_best_weights=True
                                          )
            model_checkpoint = ModelCheckpoint(monitor='val_loss',
                                               filepath=file_path, verbose=5,
                                               save_best_only=True, mode="min")
        else:
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
            x: array-like, shape `(n_samples, n_features)`
                Test samples where `n_samples` is the number of samples
                and `n_features` is the number of features.
            y: array-like, shape `(n_samples,)`
                True labels for `x`.
            **kwargs: dictionary arguments
                Legal arguments are the arguments of `Sequential.evaluate`.

        # Returns
            score: float
                Mean accuracy of predictions on `x` wrt. `y`.
        """
        kwargs = self.filter_sk_params(Sequential.evaluate_generator, kwargs)
        loss = self.model.evaluate_generator(self.train_data_generator, **kwargs)
        if isinstance(loss, list):
            return -loss[0]
        return -loss

    @property
    def history(self):
        return self.__history

    def create_gens(self, X, y, seq_length=30, batch_size=15):
        generator = TimeseriesGenerator(X, y,
                                        length=seq_length,
                                        sampling_rate=1,
                                        stride=1,
                                        batch_size=batch_size)
        return generator

    def extract_data(self, generator):
        for i in np.arange(len(generator)):
            if i == 0:
                a, b = generator[i]
            else:
                c, d = generator[i]

                a = np.vstack((a, c))
                b = np.vstack((b, d))

        return a, b
