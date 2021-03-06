from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random
import numpy as np

# PyTorch imports.
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

np.random.seed(71)


class LinearRegression(nn.Module):
    """PyTorch implementation of Linear Regression."""

    def __init__(self, batch_size=64, lr=0.01, n_epochs=1000):
        super(LinearRegression, self).__init__()
        self.batch_size = batch_size
        self.lr = lr
        self.n_epochs = n_epochs

    def get_data(self, X_train, y_train, shuffle=True):
        """Get dataset and information."""
        self.X_train = X_train
        self.y_train = y_train

        # Get the numbers of examples and inputs.
        self.n_examples, self.n_inputs = self.X_train.shape

        if shuffle:
            idx = list(range(self.n_examples))
            random.shuffle(idx)
            self.X_train = self.X_train[idx]
            self.y_train = self.y_train[idx]

    def _create_model(self):
        """Create linear regression model."""
        self.model = nn.Linear(self.n_inputs, 1)

    def forward(self, x):
        """Foward to output model."""
        y = self.model(x)
        return y

    def _create_loss(self):
        """Create squared error loss."""
        self.criterion = nn.MSELoss()

    def _create_optimizer(self):
        """Create optimizer by stochastic gradient descent."""
        self.optimizer = optim.SGD(self.model.parameters(), lr=self.lr)

    def build_graph(self):
        """Build computational graph."""
        self._create_model()
        self._create_loss()
        self._create_optimizer()

    def _fetch_batch(self):
        """Fetch batch dataset."""
        idx = list(range(self.n_examples))
        for i in range(0, self.n_examples, self.batch_size):
            idx_batch = idx[i:min(i + self.batch_size, self.n_examples)]
            yield (self.X_train.take(idx_batch, axis=0), 
                   self.y_train.take(idx_batch, axis=0))

    def fit(self):
        """Fit model."""
        for epoch in range(1, self.n_epochs + 1):
            total_loss = 0
            for X_train_b, y_train_b in self._fetch_batch():
                # Convert to Tensor from NumPy array and reshape ys.
                X_train_b, y_train_b = (
                    torch.from_numpy(X_train_b), 
                    torch.from_numpy(y_train_b).view(-1, 1))

                y_pred_b = self.model(X_train_b)
                batch_loss = self.criterion(y_pred_b, y_train_b)
                total_loss += batch_loss * X_train_b.shape[0]

                # Zero grads, performs backward pass, and update weights.
                self.optimizer.zero_grad()
                batch_loss.backward()
                self.optimizer.step()

            if epoch % 100 == 0:
                print('Epoch {0}: training loss: {1}'
                      .format(epoch, total_loss / self.n_examples))

    def get_coeff(self):
        """Get model coefficients."""
        # Detach var which require grad.
        return (self.model.bias.detach().numpy(),
                self.model.weight.detach().numpy())

    def predict(self, X):
        """Predict for new data."""
        with torch.no_grad():
            X_ = torch.from_numpy(X)
            return self.model(X_).numpy().reshape((-1,))


def main():
    import sklearn
    from sklearn.datasets import fetch_california_housing
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.linear_model import LinearRegression as LinearRegressionSklearn
    from metrics import mean_squared_error

    # Read California housing data.
    housing = fetch_california_housing()
    data = housing.data
    label = housing.target

    # Normalize features first.
    scaler = StandardScaler()
    data = scaler.fit_transform(data)

    # Split data into training and test datasets.
    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=71, shuffle=True)

    # Feature engineering for standardizing features by min-max scaler.
    min_max_scaler = MinMaxScaler()
    X_train = min_max_scaler.fit_transform(X_train_raw)
    X_test = min_max_scaler.transform(X_test_raw)

    # Convert arrays to float32.
    X_train, X_test, y_train, y_test = (
        np.float32(X_train), np.float32(X_test), 
        np.float32(y_train), np.float32(y_test)
    )

    # Train PyTorch linear regression model.
    linreg_torch = LinearRegression(batch_size=64, lr=0.1, n_epochs=1000)
    linreg_torch.get_data(X_train, y_train, shuffle=True)
    linreg_torch.build_graph()
    linreg_torch.fit()
    print(linreg_torch.get_coeff())
    y_train_ = linreg_torch.predict(X_train)
    print('Training mean squared error: {}'
           .format(mean_squared_error(y_train, y_train_)))
    y_test_ = linreg_torch.predict(X_test)
    print('Test mean squared error: {}'
           .format(mean_squared_error(y_test, y_test_)))

    # Benchmark with sklearn's linear regression model.
    linreg_sk = LinearRegressionSklearn()
    linreg_sk.fit(X_train, y_train) 
    y_train_ = linreg_sk.predict(X_train)
    print('Training mean squared error: {}'
           .format(mean_squared_error(y_train, y_train_)))
    y_test_ = linreg_sk.predict(X_test)
    print('Test mean squared error: {}'
           .format(mean_squared_error(y_test, y_test_)))


if __name__ == '__main__':
    main()
