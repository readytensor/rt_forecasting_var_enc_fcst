
import os, warnings, sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # or any {'0', '1', '2'}
warnings.filterwarnings('ignore') 

from abc import ABC, abstractmethod
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.metrics import Mean



class BaseVariationalAutoencoder(Model, ABC):
    def __init__(self,  
            encode_len,
            decode_len,
            feat_dim,
            latent_dim,
            reconstruction_wt = 5.0,
            **kwargs  ):
        super(BaseVariationalAutoencoder, self).__init__(**kwargs)
        self.encode_len = encode_len
        self.decode_len = decode_len
        self.feat_dim = feat_dim
        self.latent_dim = latent_dim
        self.reconstruction_wt = reconstruction_wt
        self.total_loss_tracker = Mean(name="total_loss")
        self.reconstruction_loss_tracker = Mean( name="reconstruction_loss" )
        self.kl_loss_tracker = Mean(name="kl_loss")
        self.encoder = None
        self.decoder = None
 

    def call(self, X):
        z_mean, _, _ = self.encoder(X)
        x_decoded = self.decoder(z_mean)
        if len(x_decoded.shape) == 1:
            x_decoded = x_decoded.reshape((1, -1))
        return x_decoded


    def get_num_trainable_variables(self):
        trainableParams = int(np.sum([np.prod(v.get_shape()) for v in self.trainable_weights]))
        nonTrainableParams = int(np.sum([np.prod(v.get_shape()) for v in self.non_trainable_weights]))
        totalParams = trainableParams + nonTrainableParams
        return trainableParams, nonTrainableParams, totalParams

    def get_prior_samples(self, Z):
        samples = self.decoder.predict(Z)
        return samples


    @abstractmethod
    def _get_encoder(self, **kwargs):
        raise NotImplementedError


    @abstractmethod
    def _get_decoder(self, **kwargs):
        raise NotImplementedError

    
    def summary(self):
        self.encoder.summary()
        self.decoder.summary()


    def train_step(self, data): 
        X, Y = data
        with tf.GradientTape() as tape:
            z_mean, z_log_var, z = self.encoder(X)
            reconstruction = self.decoder(z)
            err = tf.math.squared_difference(Y, reconstruction)
            reconstruction_loss = tf.reduce_mean(err)
            kl_loss = -0.5 * (1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var))
            kl_loss = tf.reduce_mean(kl_loss)
            total_loss = self.reconstruction_wt * reconstruction_loss + kl_loss

        grads = tape.gradient(total_loss, self.trainable_weights)
        self.optimizer.apply_gradients(zip(grads, self.trainable_weights))
        self.total_loss_tracker.update_state(total_loss)
        self.reconstruction_loss_tracker.update_state(reconstruction_loss)
        self.kl_loss_tracker.update_state(kl_loss)
        return {
            "loss": self.total_loss_tracker.result(),
            "reconstruction_loss": self.reconstruction_loss_tracker.result(),
            "kl_loss": self.kl_loss_tracker.result(),
        }


    def test_step(self, data):
        X, Y = data
        z_mean, z_log_var, z = self.encoder(X)
        reconstruction = self.decoder(z)
        err = tf.math.squared_difference(Y, reconstruction)
        reconstruction_loss = tf.reduce_sum(err)
        kl_loss = -0.5 * (1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var))
        kl_loss = tf.reduce_sum(kl_loss)
        total_loss = self.reconstruction_wt * reconstruction_loss + kl_loss
        self.total_loss_tracker.update_state(total_loss)
        self.reconstruction_loss_tracker.update_state(reconstruction_loss)
        self.kl_loss_tracker.update_state(kl_loss)

        return {
            "loss": self.total_loss_tracker.result(),
            "reconstruction_loss": self.reconstruction_loss_tracker.result(),
            "kl_loss": self.kl_loss_tracker.result(),
        }
