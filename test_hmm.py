import numpy as np
import pytest
import hmmlearn.hmm
from scipy.special import logsumexp

from hmmidunnomaybe import HMM


def get_hmm_learn_model(hmm):
    hmm_learn_model = hmmlearn.hmm.MultinomialHMM(
        n_components=hmm.A.shape[0], init_params="", tol=0, n_iter=hmm.n_iter
    )
    hmm_learn_model.startprob_ = hmm.pi
    hmm_learn_model.transmat_ = hmm.A
    hmm_learn_model.emissionprob_ = hmm.B

    return hmm_learn_model


def to_weird_format(sequences):
    # Please don't ask
    return {
        "X": np.array(sequences).ravel().reshape(-1, 1),
        "lengths": [sequences.shape[1]] * sequences.shape[0],
    }


@pytest.fixture
def toy_params():
    # 2 hidden states, 3 observable states
    pi = np.array([0.6, 0.4])
    A = np.array([[0.7, 0.3], [0.4, 0.6]])
    B = np.array([[0.1, 0.4, 0.5], [0.6, 0.3, 0.1]])

    return pi, A, B


def test_likelihood_alpha_beta(toy_params):
    # Make sure computing likelihood with just alpha is the same as computing
    # it with alpha and beta
    # For all t, the likelihood is equal to sum (alpha[:, t] * beta[:, t])

    def log_likelihood2(hmm, seq):
        sequences = np.array(seq)
        n_obs = sequences.shape[0]
        log_alpha = np.empty(shape=(hmm.n_hidden_states, n_obs))
        log_beta = np.empty(shape=(hmm.n_hidden_states, n_obs))
        hmm._forward(seq, log_alpha)
        hmm._backward(seq, log_beta)
        # return likelihoods computed at all ts
        return logsumexp(log_alpha + log_beta, axis=0)

    pi, A, B = toy_params

    hmm = HMM(pi, A, B)
    X = np.array([[0, 1, 2, 0, 1, 2, 0, 1]])
    expected_likelihood = hmm.log_likelihood(X)

    np.testing.assert_allclose(expected_likelihood, log_likelihood2(hmm, X[0]))


def test_loglikelihood(toy_params):
    # Basic test making sure hmmlearn has the same results

    pi, A, B = toy_params

    hmm = HMM(pi, A, B)
    hmm_learn_model = get_hmm_learn_model(hmm)

    rng = np.random.RandomState(0)
    n_seq, n_obs = 10, 100
    sequences = rng.randint(B.shape[1], size=(n_seq, n_obs))

    expected = hmm_learn_model.score(**to_weird_format(sequences))
    assert hmm.log_likelihood(sequences) == pytest.approx(expected)


def test_decode(toy_params):
    # Basic test making sure hmmlearn has the same results

    pi, A, B = toy_params

    hmm = HMM(pi, A, B)
    hmm_learn_model = get_hmm_learn_model(hmm)

    rng = np.random.RandomState(0)
    n_seq, n_obs = 10, 100
    sequences = rng.randint(B.shape[1], size=(n_seq, n_obs))

    expected = hmm_learn_model.decode(**to_weird_format(sequences))[1].reshape(
        sequences.shape
    )
    assert np.all(hmm.decode(sequences) == expected)


def test_EM(toy_params):
    # Basic test making sure hmmlearn has the same results

    pi, A, B = toy_params
    n_iter = 10

    hmm = HMM(pi, A, B, n_iter=n_iter)
    hmm_learn_model = get_hmm_learn_model(hmm)
    hmm._enable_sanity_checks = True

    rng = np.random.RandomState(0)
    n_seq, n_obs = 10, 100
    sequences = rng.randint(B.shape[1], size=(n_seq, n_obs))

    hmm.EM(sequences)
    hmm_learn_model.fit(**to_weird_format(sequences))

    np.testing.assert_allclose(hmm.pi, hmm_learn_model.startprob_)
    np.testing.assert_allclose(hmm.A, hmm_learn_model.transmat_)
    np.testing.assert_allclose(hmm.B, hmm_learn_model.emissionprob_)


def test_sample(toy_params):
    # Make sure shapes are  as expected
    # Also make sure seed behaves properly

    pi, A, B = toy_params
    hmm = HMM(pi, A, B)
    n_obs, n_seq = 10, 20

    obs_sequences, hidden_state_sequences = hmm.sample(n_seq=n_seq, n_obs=n_obs, seed=0)
    assert obs_sequences.shape == hidden_state_sequences.shape == (n_seq, n_obs)

    obs_sequences_same, hidden_state_sequences_same = hmm.sample(
        n_seq=n_seq, n_obs=n_obs, seed=0
    )
    assert np.all(obs_sequences == obs_sequences_same)
    assert np.all(hidden_state_sequences == hidden_state_sequences_same)

    obs_sequences_diff, hidden_state_sequences_diff = hmm.sample(
        n_seq=n_seq, n_obs=n_obs, seed=1
    )
    assert not np.all(obs_sequences == obs_sequences_diff)
    assert not np.all(hidden_state_sequences == hidden_state_sequences_diff)
