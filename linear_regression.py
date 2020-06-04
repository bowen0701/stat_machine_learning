from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import numpy as np

import tensorflow as tf
from mxnet import nd, autograd, init, gluon
from mxnet.gluon import data as gdata
from mxnet.gluon import nn
from mxnet.gluon import loss as gloss


# Reset default graph.
def reset_tf_graph(seed=71):
    tf.reset_default_graph()
    tf.set_random_seed(seed)
    np.random.seed(seed)


class LinearRegressionTF(object):
    """A TensorFlow implementation of Linear Regression."""
    def __init__(self, batch_size=64, learning_rate=0.01, n_epochs=1000):
        self._batch_size = batch_size
        self._n_epochs = n_epochs
        self._learning_rate = learning_rate

    def get_dataset(self, X_train, y_train, shuffle=True):
        self._X_train = X_train
        self._y_train = y_train

        # Get the numbers of examples and inputs.
        self._n_examples = self._X_train.shape[0]
        self._n_inputs = self._X_train.shape[1]

        idx = list(range(self._n_examples))
        if shuffle:
            random.shuffle(idx)
        self._X_train = self._X_train[idx]
        self._y_train = self._y_train[idx]
    
    def _create_placeholders(self):
        self._X = tf.placeholder(tf.float32, shape=(None, self._n_inputs), name='X')
        self._y = tf.placeholder(tf.float32, shape=(None, 1), name='y')
    
    def _create_weights(self):
        self._w = tf.get_variable(shape=(self._n_inputs, 1), 
                                  initializer=tf.random_normal_initializer(0, 0.01), 
                                  name='weights')
        self._b = tf.get_variable(shape=(1, 1), 
                                  initializer=tf.zeros_initializer(), name='bias')
    
    def _create_model(self):
        self._y_pred = tf.add(tf.matmul(self._X, self._w), self._b, name='y_pred')
    
    def _create_loss(self):
        # Mean squared error loss.
        self._error = self._y_pred - self._y
        self._loss = tf.reduce_mean(tf.square(self._error), name='loss')
    
    def _create_optimizer(self):
        # Gradient descent optimization.
        self._optimizer = (
            tf.train.GradientDescentOptimizer(learning_rate=self._learning_rate)
            .minimize(self._loss))

    def build_graph(self):
        self._create_placeholders()
        self._create_weights()
        self._create_model()
        self._create_loss()
        self._create_optimizer()

    def _fetch_batch(self):
        idx = list(range(self._n_examples))
        for i in range(0, self._n_examples, self._batch_size):
            idx_batch = idx[i:min(i + self._batch_size, self._n_examples)]
            yield (self._X_train[idx_batch, :], self._y_train[idx_batch, :])

    def train_model(self):
        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())

            for epoch in range(self._n_epochs):
                total_loss = 0

                for X_train_b, y_train_b in self._fetch_batch():
                    feed_dict = {self._X: X_train_b, self._y: y_train_b}
                    _, batch_loss = sess.run([self._optimizer, self._loss],
                                             feed_dict=feed_dict)
                    total_loss += batch_loss

                if epoch % 100 == 0:
                    print('Epoch {0}: training loss: {1}'
                          .format(epoch, total_loss / self._n_examples))

            w_out, b_out = sess.run([self._w, self._b])
            print('Weight:\n{}'.format(w_out))
            print('Bias: {}'.format(b_out))


class LinearRegressionMX(object):
    """MXNet implementation of Linear Regression."""
    def __init__(self, batch_size=10, lr=0.01, n_epochs=5):
        self.batch_size = batch_size
        self.lr = lr
        self.n_epochs = n_epochs
    
    def _linreg(self, X, w, b):
        return nd.dot(X, w) + b
    
    def _squared_loss(self, y_hat, y):
        return (y_hat - y.reshape(y_hat.shape)) ** 2 / 2

    def _weights_init(self):
        w = nd.random.normal(scale=0.01, shape=(self.n_inputs, 1))
        b = nd.zeros(shape=(1,))
        params = [w, b]
        for param in params:
            # Attach gradient for automatic differentiation.
            param.attach_grad()
        return params
    
    def _sgd(self, w, d):
        for param in [w, d]:
            # Take parameter's gradient from auto diff output.
            param[:] = param - self.lr * param.grad / self.batch_size

    def _data_iter(self):
        idx = list(range(self.n_examples))
        random.shuffle(idx)
        for i in range(0, self.n_examples, self.batch_size):
            idx_batch = nd.array(idx[i:min(i + self.batch_size, self.n_examples)])
            yield self.X_train.take(idx_batch), self.y_train.take(idx_batch)
    
    def fit(self, X_train, y_train):
        self.X_train = X_train
        self.y_train = y_train
        self.n_examples, self.n_inputs = X_train.shape

        net = self._linreg
        loss = self._squared_loss
        w, b = self._weights_init()

        for epoch in range(self.n_epochs):
            for X, y in self._data_iter():
                # Record auto diff & perform backward differention.
                with autograd.record():
                    l = loss(net(X, w, b), y)
                l.backward()
                self._sgd(w, b)

            train_loss = loss(net(self.X_train, w, b), self.y_train)
            print('epoch {0}: loss {1}'
                  .format(epoch + 1, train_loss.mean().asnumpy()))
        
        self.net = net
        self.w, self.b = w, b
        return self

    def get_coeff(self):
        return self.b, self.w.reshape((-1,))

    def predict(self, X_test):
        return self.net(X_test, self.w, self.b).reshape((-1,))


class LinearRegressionMXGluon(object):
    """MXNet-Gluon implementation of Linear Regression."""
    def __init__(self, batch_size=10, lr=0.01, n_epochs=5):
        self.batch_size = batch_size
        self.lr = lr
        self.n_epochs = n_epochs

    def _linreg(self):
        net = nn.Sequential()
        net.add(nn.Dense(1))
        return net

    def _squared_loss(self):
        return gloss.L2Loss()

    def _weights_init(self, net):
        net.initialize(init.Normal(sigma=0.01))

    def _sgd_trainer(self, net):
        return gluon.Trainer(
            net.collect_params(), 'sgd', {'learning_rate': self.lr})

    def _data_iter(self):
        dataset = gdata.ArrayDataset(self.X_train, self.y_train)
        return gdata.DataLoader(dataset, self.batch_size, shuffle=True)

    def fit(self, X_train, y_train):
        self.X_train = X_train
        self.y_train = y_train

        net = self._linreg()
        loss = self._squared_loss()
        self._weights_init(net)
        trainer = self._sgd_trainer(net)

        for epoch in list(range(self.n_epochs)):
            for X, y in self._data_iter():
                with autograd.record():
                    l = loss(net(X), y)
                l.backward()
                trainer.step(self.batch_size)

            train_loss = loss(net(self.X_train), self.y_train)
            print('epoch {0}: loss {1}'
                  .format(epoch + 1, train_loss.mean().asnumpy()))

        self.net = net
        return self

    def get_coeff(self):
        _coef = self.net[0]
        return _coef.bias.data(), _coef.weight.data().reshape((-1,))

    def predict(self, X_test):
        return self.net(X_test).reshape((-1,))


def main():
    from sklearn.datasets import fetch_california_housing
    from sklearn.preprocessing import StandardScaler

    # Read California housing data.
    housing = fetch_california_housing()
    data = housing.data
    label = housing.target.reshape(-1, 1)

    # Important: Normalize features first.
    scaler = StandardScaler()
    data = scaler.fit_transform(data)

    # Split data into training/test datasets.
    test_ratio = 0.2
    test_size = int(data.shape[0] * test_ratio)

    X_train = data[:-test_size]
    X_test = data[-test_size:]
    y_train = label[:-test_size]
    y_test = label[-test_size:]

    # TODO: Train Numpy linear regression model.

    # Train TensorFlow linear regression model.
    reset_tf_graph()
    linreg = LinearRegressionTF()
    linreg.get_dataset(X_train, y_train)
    linreg.build_graph()
    linreg.train_model()

    # TODO: Train MXNet linear regression model.

    # TODO: Train MXNet-Gluon linear regression model.


if __name__ == '__main__':
    main()