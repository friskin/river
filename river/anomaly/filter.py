import math

from river import anomaly, stats


class ThresholdFilter(anomaly.base.AnomalyFilter):
    """Threshold anomaly filter.

    Parameters
    ----------
    anomaly_detector
        An anomaly detector.
    threshold
        A threshold above which to classify an anomaly score as anomalous.
    protect_anomaly_detector
        Indicates whether or not the anomaly detector should be updated when the anomaly score is
        anomalous. If the data contains sporadic anomalies, then the anomaly detector should likely
        not be updated. Indeed, if it learns the anomaly score, then it will slowly start to
        consider anomalous anomaly scores as normal. This might be desirable, for instance in the
        case of drift.

    Examples
    --------

    Anomaly filters can be used as part of a pipeline. For instance, we might want to filter out
    anomalous observations so as not to corrupt a supervised model. As an example, let's take
    the `datasets.WaterFlow` dataset. Some of the samples have anomalous target variables because
    of human interventions. We don't want our model to learn these values.

    >>> from river import datasets
    >>> from river import metrics
    >>> from river import time_series

    >>> dataset = datasets.WaterFlow()
    >>> metric = metrics.SMAPE()

    >>> period = 24  # 24 samples per day

    >>> model = (
    ...     anomaly.ThresholdFilter(
    ...         anomaly.GaussianScorer(
    ...             window_size=period * 7,  # 7 days
    ...             grace_period=30
    ...         ),
    ...         threshold=0.995
    ...     ) |
    ...     time_series.HoltWinters(
    ...         alpha=0.3,
    ...         beta=0.1,
    ...         multiplicative=False
    ...     )
    ... )

    >>> time_series.evaluate(
    ...     dataset,
    ...     model,
    ...     metric,
    ...     horizon=period
    ... )
    +1  SMAPE: 4.220171
    +2  SMAPE: 4.322648
    +3  SMAPE: 4.418546
    +4  SMAPE: 4.504986
    +5  SMAPE: 4.57924
    +6  SMAPE: 4.64123
    +7  SMAPE: 4.694042
    +8  SMAPE: 4.740753
    +9  SMAPE: 4.777291
    +10 SMAPE: 4.804558
    +11 SMAPE: 4.828114
    +12 SMAPE: 4.849823
    +13 SMAPE: 4.865871
    +14 SMAPE: 4.871972
    +15 SMAPE: 4.866274
    +16 SMAPE: 4.842614
    +17 SMAPE: 4.806214
    +18 SMAPE: 4.763355
    +19 SMAPE: 4.713455
    +20 SMAPE: 4.672062
    +21 SMAPE: 4.659102
    +22 SMAPE: 4.693496
    +23 SMAPE: 4.773707
    +24 SMAPE: 4.880654

    """

    def __init__(
        self, anomaly_detector, threshold: float, protect_anomaly_detector=True
    ):
        super().__init__(
            anomaly_detector=anomaly_detector,
            protect_anomaly_detector=protect_anomaly_detector,
        )
        self.threshold = threshold

    def classify(self, score):
        return score >= self.threshold


class QuantileFilter(anomaly.base.AnomalyFilter):
    """Threshold anomaly filter.

    Parameters
    ----------
    anomaly_detector
        An anomaly detector.
    q
        The quantile level above which to classify an anomaly score as anomalous.
    protect_anomaly_detector
        Indicates whether or not the anomaly detector should be updated when the anomaly score is
        anomalous. If the data contains sporadic anomalies, then the anomaly detector should likely
        not be updated. Indeed, if it learns the anomaly score, then it will slowly start to
        consider anomalous anomaly scores as normal. This might be desirable, for instance in the
        case of drift.

    Examples
    --------

    >>> from river import anomaly
    >>> from river import compose
    >>> from river import datasets
    >>> from river import metrics
    >>> from river import preprocessing

    >>> model = compose.Pipeline(
    ...     preprocessing.MinMaxScaler(),
    ...     anomaly.QuantileFilter(
    ...         anomaly.HalfSpaceTrees(seed=42),
    ...         q=0.95
    ...     )
    ... )

    >>> report = metrics.ClassificationReport()

    >>> for x, y in datasets.CreditCard().take(8000):
    ...     score = model.score_one(x)
    ...     is_anomaly = model['QuantileFilter'].classify(score)
    ...     model = model.learn_one(x)
    ...     report = report.update(y, is_anomaly)

    >>> report
                   Precision   Recall   F1       Support
    <BLANKLINE>
           0      99.91%   97.78%   98.83%      7975
           1       9.23%   72.00%   16.36%        25
    <BLANKLINE>
       Macro      54.57%   84.89%   57.60%
       Micro      97.70%   97.70%   97.70%
    Weighted      99.63%   97.70%   98.58%
    <BLANKLINE>
                     97.70% accuracy

    """

    def __init__(self, anomaly_detector, q: float, protect_anomaly_detector=True):
        super().__init__(
            anomaly_detector=anomaly_detector,
            protect_anomaly_detector=protect_anomaly_detector,
        )
        self.quantile = stats.Quantile(q=q)

    @property
    def q(self):
        return self.quantile.q

    def classify(self, score):
        return score >= (self.quantile.get() or math.inf)

    def learn_one(self, *args):
        score = self.score_one(*args)
        if self.protect_anomaly_detector and not self.classify(score):
            self.anomaly_detector.learn_one(*args)
        self.quantile.update(score)
        return self
