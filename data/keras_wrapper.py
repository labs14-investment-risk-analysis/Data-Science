from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras.wrappers.scikit_learn import KerasRegressor
from keras.preprocessing.sequence import TimeseriesGenerator
from sklearn.model_selection import train_test_split

import types


class KerasRegressorGenerator(KerasRegressor):
    """Use parameters: 'seq_length', 'batch_size', and 'epochs' in param_grid along with model parameters"""

    def fit(self, X, y **kwargs):
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

        train_data_generator = self.create_gens(X_train, y_train, seq_length=self.sk_params['seq_length'],
                                                    batch_size=self.sk_params['batch_size'])

        if 'val' in kwargs:

            early_stopping = EarlyStopping( patience=5, verbose=5, mode="auto", restore_best_weights=True)
            model_checkpoint = ModelCheckpoint("results/best_weights.{epoch:02d}-{loss:.5f}.hdf5", verbose=5,
                                               save_best_only=True, mode="auto")
        else:
            val_gen = None
            early_stopping = EarlyStopping(monitor="acc", patience=3, verbose=5, mode="auto", restore_best_weights=True)
            model_checkpoint = ModelCheckpoint("results/best_weights.{epoch:02d}-{loss:.5f}.hdf5", monitor="acc",
                                               verbose=5, save_best_only=True, mode="auto")

        callbacks = [early_stopping, model_checkpoint]

        epochs = self.sk_params['epochs'] if 'epochs' in self.sk_params else 100

        self.__history = self.model.fit_generator(
            train_gen,
            epochs=epochs,
            validation_data=val_gen,
            callbacks=callbacks
        )

        return self.__history

    def score(self, X, y, **kwargs):
        kwargs = self.filter_sk_params(Sequential.evaluate, kwargs)

        loss_name = self.model.loss
        if hasattr(loss_name, '__name__'):
            loss_name = loss_name.__name__
        outputs = self.model.evaluate(X, y, **kwargs)
        if type(outputs) is not list:
            outputs = [outputs]
        for name, output in zip(self.model.metrics_names, outputs):
            if name == 'acc':
                return output
        raise Exception('The model is not configured to compute accuracy. '
                        'You should pass `metrics=["accuracy"]` to '
                        'the `model.compile()` method.')

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