import os, sys, random, copy
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estimators.bandits import ips
from estimators.bandits import snips
from estimators.bandits import mle
from estimators.bandits import cressieread
from estimators.bandits import cats_utils
from estimators.bandits import gaussian
from estimators.bandits import clopper_pearson
from estimators.test.utils import Helper

def test_bandits_unit_test():
    listofestimators = [(ips.Estimator(), 2.0), (snips.Estimator(), 1.0), (mle.Estimator(), 1.0), (cressieread.Estimator(), 1.0)]
    
    p_log = 0.3
    p_pred = 0.6
    reward = 1

    for Estimator in listofestimators:
        Estimator[0].add_example(p_log, reward, p_pred)
        assert Estimator[0].get() == Estimator[1]


def test_bandits():
    ''' To test correctness of estimators: Compare the expected value with value returned by Estimator.get()'''

    # The tuple (Estimator, expected value) for each estimator is stored in listofestimators
    listofestimators = [(ips.Estimator(), 1), (snips.Estimator(), 1), (mle.Estimator(), 1), (cressieread.Estimator(), 1)]

    def datagen():
        return  {'p_log': 1,
                'r': 1,
                'p_pred': 1}

    estimates = Helper.get_estimate(datagen, listofestimators=[l[0] for l in listofestimators], num_examples=4)

    for Estimator, estimate in zip(listofestimators, estimates):
        Helper.assert_is_close(Estimator[1], estimate)


def test_narrowing_intervals():
    ''' To test for narrowing intervals; Number of examples increase => narrowing CI '''

    listofintervals = [cressieread.Interval(), gaussian.Interval(), clopper_pearson.Interval()]

    def datagen(epsilon, delta=0.5):
        # Logged Policy
        # 0 - (1-epsilon) : Reward is Bernoulli(delta)
        # 1 - epsilon : Reward is Bernoulli(1-delta)

        # p_pred: 1 if action is chosen, 0 if action not chosen

        # policy to estimate
        # (delta), (1-delta) reward from a Bernoulli distribution - for probability p_pred

        chosen = int(random.random() < epsilon)
        return {'p_log': epsilon if chosen == 1 else 1 - epsilon,
                'r': int(random.random() < 1-delta) if chosen == 1 else int(random.random() < delta),
                'p_pred': int(chosen==1)}

    intervals_n1 = Helper.get_estimate(lambda: datagen(epsilon=0.5), listofintervals, num_examples=100)
    intervals_n2 = Helper.get_estimate(lambda: datagen(epsilon=0.5), listofintervals, num_examples=10000)

    for interval_n1, interval_n2 in zip(intervals_n1, intervals_n2):
        width_n1 = interval_n1[1] - interval_n1[0]
        width_n2 = interval_n2[1] - interval_n2[0]
        assert width_n1 > 0
        assert width_n2 > 0
        assert width_n2 < width_n1


def test_cats_ips():
    ips_estimator = ips.Estimator()
    snips_estimator = snips.Estimator()

    prob_logs = [0.151704, 0.006250, 0.086, 0.086, 0.086]
    action_logs = [15.0, 3.89, 22.3, 17.34, 31]
    rewards = [0.1, 0.2, 0, 1.0, 1.0]

    max_value = 32
    bandwidth = 1
    cats_transformer = cats_utils.CatsTransformer(num_actions=8, min_value=0, max_value=max_value, bandwidth=bandwidth)

    for logged_action, r, logged_prob in zip(action_logs, rewards, prob_logs):
        data = {}
        data['a'] = logged_action
        data['cost'] = r
        data['p'] = logged_prob
        if logged_action < (max_value / 2.0):
            pred_action = logged_action + 2 * bandwidth
            data = cats_transformer.transform(data, pred_action) # pred_action should be too far away, so pred_p should be 0
            assert data['pred_p'] == 0.0
        else:
            pred_action = logged_action
            data = cats_transformer.transform(data, logged_action) # same action, so pred_p should be 1
            assert data['pred_p'] == 1.0 / (2 * bandwidth)

        ips_estimator.add_example(data['p'], r, data['pred_p'])
        snips_estimator.add_example(data['p'], r, data['pred_p'])
        assert ips_estimator.get() >= snips_estimator.get()


def test_cats_transformer_on_edges():
    prob_logs = [0.151704, 0.006250, 0.086, 0.086]
    action_logs = [0, 1, 31, 32]
    rewards = [1.0, 1.0, 1.0, 1.0]

    max_value = 32
    bandwidth = 2
    cats_transformer = cats_utils.CatsTransformer(num_actions=8, min_value=0, max_value=max_value, bandwidth=bandwidth)

    for logged_action, r, logged_prob in zip(action_logs, rewards, prob_logs):
        data = {}
        data['a'] = logged_action
        data['cost'] = r
        data['p'] = logged_prob
    
        pred_action = logged_action
        data = cats_transformer.transform(data, logged_action) # same action, so pred_p should be 1
        assert data['pred_p'] == 1.0 / (2 * bandwidth)


def test_cats_baseline():
    max_value = 32
    min_value = 0
    bandwidth = 1
    num_actions = 8
    cats_transformer = cats_utils.CatsTransformer(num_actions=num_actions, min_value=min_value, max_value=max_value, bandwidth=bandwidth)
    baseline = cats_transformer.get_baseline1_prediction()
    ## unit range is 4, min_value is 0 so baseline action should be the centre of the firt unit range, starting off from min_value i.e. 2
    assert baseline == 2

    max_value = 33
    min_value = 1
    bandwidth = 1
    num_actions = 8
    cats_transformer = cats_utils.CatsTransformer(num_actions=num_actions, min_value=min_value, max_value=max_value, bandwidth=bandwidth)
    baseline = cats_transformer.get_baseline1_prediction()
    ## unit range is 4, min_value is 1 so baseline action should be the centre of the firt unit range, starting off from min_value i.e. 3
    assert baseline == 3