#!/usr/bin/env python
# CREATED:2013-03-11 18:14:30 by Brian McFee <brm2132@columbia.edu>
#  unit tests for librosa.beat

from __future__ import print_function
from nose.tools import raises, eq_

# Disable cache
import os
try:
    os.environ.pop('LIBROSA_CACHE_DIR')
except:
    pass

import matplotlib
matplotlib.use('Agg')

import warnings

import numpy as np
import librosa

__EXAMPLE_FILE = 'data/test1_22050.wav'


def test_onset_strength_audio():

    def __test(y, sr, feature, n_fft, hop_length, lag, max_size, detrend, center, aggregate):

        oenv = librosa.onset.onset_strength(y=y, sr=sr,
                                            S=None,
                                            detrend=detrend,
                                            center=center,
                                            aggregate=aggregate,
                                            feature=feature,
                                            n_fft=n_fft,
                                            hop_length=hop_length,
                                            lag=lag,
                                            max_size=max_size)

        assert oenv.ndim == 1

        S = librosa.feature.melspectrogram(y=y,
                                           n_fft=n_fft,
                                           hop_length=hop_length)

        target_shape = S.shape[-1]

        #if center:
        #    target_shape += n_fft // (2 * hop_length)

        if not detrend:
            assert np.all(oenv >= 0)

        eq_(oenv.shape[-1], target_shape)

    y, sr = librosa.load(__EXAMPLE_FILE)

    for feature in [None,
                    librosa.feature.melspectrogram,
                    librosa.feature.chroma_stft]:
        for n_fft in [512, 2048]:
            for hop_length in [n_fft // 2, n_fft // 4]:
                for lag in [0, 1, 2]:
                    for max_size in [0, 1, 2]:
                        for detrend in [False, True]:
                            for center in [False, True]:
                                for aggregate in [None, np.mean, np.max]:
                                    if lag < 1 or max_size < 1:
                                        tf = raises(librosa.ParameterError)(__test)
                                    else:
                                        tf = __test

                                    yield (tf, y, sr, feature, n_fft,
                                           hop_length, lag, max_size, detrend, center, aggregate)

                                    tf = raises(librosa.ParameterError)(__test)
                                    yield (tf, None, sr, feature, n_fft,
                                           hop_length, lag, max_size, detrend, center, aggregate)


def test_onset_strength_spectrogram():

    def __test(S, sr, feature, n_fft, hop_length, detrend, center):

        oenv = librosa.onset.onset_strength(y=None, sr=sr,
                                            S=S,
                                            detrend=detrend,
                                            center=center,
                                            aggregate=aggregate,
                                            feature=feature,
                                            n_fft=n_fft,
                                            hop_length=hop_length)

        assert oenv.ndim == 1

        target_shape = S.shape[-1]

        #if center:
        #    target_shape += n_fft // (2 * hop_length)

        if not detrend:
            assert np.all(oenv >= 0)

        eq_(oenv.shape[-1], target_shape)

    y, sr = librosa.load(__EXAMPLE_FILE)
    S = librosa.feature.melspectrogram(y=y, sr=sr)

    for feature in [None,
                    librosa.feature.melspectrogram,
                    librosa.feature.chroma_stft]:
        for n_fft in [512, 2048]:
            for hop_length in [n_fft // 2, n_fft // 4]:
                for detrend in [False, True]:
                    for center in [False, True]:
                        for aggregate in [None, np.mean, np.max]:
                            yield (__test, S, sr, feature, n_fft,
                                   hop_length, detrend, center)
                            tf = raises(librosa.ParameterError)(__test)
                            yield (tf, None, sr, feature, n_fft,
                                   hop_length, detrend, center)


def test_onset_strength_multi():

    y, sr = librosa.load(__EXAMPLE_FILE)
    S = librosa.feature.melspectrogram(y=y, sr=sr)

    channels = np.linspace(0, S.shape[0], num=5).astype(int)

    for lag in [1, 2, 3]:
        for max_size in [1]:
            # We only test with max_size=1 here to make the sub-band slicing test simple
            odf_multi = librosa.onset.onset_strength_multi(S=S,
                                                           lag=lag, max_size=1,
                                                           channels=channels)

            eq_(len(odf_multi), len(channels) - 1)

            for i, (s, t) in enumerate(zip(channels, channels[1:])):
                odf_single = librosa.onset.onset_strength(S=S[s:t],
                                                          lag=lag,
                                                          max_size=1)
                assert np.allclose(odf_single, odf_multi[i])


def test_onset_detect_real():

    def __test(y, sr, oenv, hop_length):

        onsets = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=oenv,
                                            hop_length=hop_length)

        assert np.all(onsets > 0)
        assert np.all(onsets < len(y) * sr // hop_length)
        if oenv is not None:
            assert np.all(onsets < len(oenv))

    y, sr = librosa.load(__EXAMPLE_FILE)

    # Test with no signal
    yield raises(librosa.ParameterError)(__test), None, sr, None, 512

    for hop_length in [64, 512, 2048]:
        yield __test, y, sr, None, hop_length
        oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        yield __test, y, sr, oenv, hop_length


def test_onset_detect_const():

    def __test(y, sr, oenv, hop_length):

        onsets = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=oenv,
                                            hop_length=hop_length)

        eq_(len(onsets), 0)

    sr = 22050
    duration = 3.0
    for f in [np.zeros, np.ones]:
        y = f(int(duration * sr))
        for hop_length in [64, 512, 2048]:
            yield __test, y, sr, None, hop_length
            yield __test, -y, sr, None, hop_length
            oenv = librosa.onset.onset_strength(y=y,
                                                sr=sr,
                                                hop_length=hop_length)
            yield __test, y, sr, oenv, hop_length


def test_onset_strength_deprecated():

    y, sr = librosa.load(__EXAMPLE_FILE)

    def __test(centering):

        no_warning = (centering is None)

        warnings.resetwarnings()
        warnings.simplefilter('always')
        with warnings.catch_warnings(record=True) as out:
            librosa.onset.onset_strength(y=y, sr=sr, centering=centering)

            if no_warning:
                eq_(out, [])
            else:
                assert len(out) > 0
                assert out[0].category is DeprecationWarning
                assert 'deprecated' in str(out[0].message).lower()


    for centering in [True, False, None]:
        yield __test, centering
