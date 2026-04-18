"""
stats.py - Statistical Testing
================================
PRINCIPLE:

  THREE STATISTICAL METHODS used in Staresina 2015:

  1. ONE-SAMPLE T-TEST (power increase):
     Tests if spindle power during SO up-state is significantly > 0
     (i.e., greater than baseline). Applied across all subjects.
     H0: mean power change = 0
     H1: mean power change > 0 (one-tailed)

  2. V-TEST (circular statistics for preferred phase):
     Tests if preferred phases across subjects are non-uniform AND
     clustered around a predicted direction (e.g., expected at SO peak).
     V-test is more powerful than Rayleigh test when the expected
     direction is known a priori.
     H0: phases are uniformly distributed (no PAC)
     H1: phases cluster around the predicted direction

  3. CLUSTER-BASED PERMUTATION TEST (for TFR maps):
     Controls for multiple comparisons when testing significance
     across a time x frequency matrix.
     PRINCIPLE:
       - Compute t-stats for every time-frequency point
       - Find contiguous significant clusters (adjacent points all p<0.05)
       - Sum the t-stats within each cluster = cluster statistic
       - Permute condition labels N times, find max cluster statistic
       - Real cluster is significant if its stat > 95th percentile of null
     This avoids the stringent Bonferroni correction that would be too
     conservative for correlated time-frequency data.
"""

import numpy as np
from scipy import stats


def power_increase_ttest(group_power: np.ndarray,
                          time_window: tuple = (-0.5, 0.5),
                          times: np.ndarray = None,
                          freq_band: tuple = (12, 16),
                          freqs: np.ndarray = None) -> dict:
    """
    One-sample t-test: is spindle power significantly increased around event?

    PRINCIPLE:
      For each subject, compute mean spindle-band power in the event window
      minus mean power in the baseline window (already subtracted if
      TFR is baseline-normalized). Then test if group mean > 0.

    Parameters
    ----------
    group_power : np.ndarray (n_subjects, n_freqs, n_times)
    time_window : tuple (start_s, end_s) for the test window
    times : np.ndarray (n_times,)
    freq_band : tuple (lo_hz, hi_hz) for the frequency band of interest
    freqs : np.ndarray (n_freqs,)

    Returns
    -------
    dict with 't_stat', 'p_value', 'n_subjects', 'mean_effect', 'sem_effect'
    """
    n_sub, n_freq, n_time = group_power.shape

    # Select time and frequency indices
    if times is None:
        times = np.linspace(-2, 2, n_time)
    if freqs is None:
        freqs = np.logspace(np.log10(1), np.log10(120), n_freq)

    t_idx = (times >= time_window[0]) & (times <= time_window[1])
    f_idx = (freqs >= freq_band[0]) & (freqs <= freq_band[1])

    # Mean power in band and window for each subject
    subject_means = group_power[:, f_idx, :][:, :, t_idx].mean(axis=(1, 2))

    t_stat, p_value = stats.ttest_1samp(subject_means, popmean=0, alternative='greater')
    return {
        't_stat': float(t_stat),
        'p_value': float(p_value),
        'n_subjects': n_sub,
        'mean_effect': float(subject_means.mean()),
        'sem_effect': float(stats.sem(subject_means)),
    }


def v_test(preferred_phases: np.ndarray,
           expected_direction: float = 0.0) -> dict:
    """
    V-test for circular statistics (Berens 2009, CircStat toolbox).

    PRINCIPLE:
      Tests if a set of angles (preferred phases) is non-uniformly
      distributed AND clustered around a pre-specified direction.

      V = 2 * N * R_bar * cos(mean_angle - expected_direction)
      where R_bar = mean resultant length (how clustered the angles are)

      The V statistic is converted to a p-value using a normal approximation.

    Parameters
    ----------
    preferred_phases : np.ndarray (n_subjects,), angles in radians [-pi, pi]
    expected_direction : float, expected mean direction in radians
                         (0.0 = SO up-state peak, typically)

    Returns
    -------
    dict with 'V_stat', 'p_value', 'mean_direction', 'mean_resultant_length'
    """
    n = len(preferred_phases)
    if n < 3:
        return {'V_stat': np.nan, 'p_value': np.nan,
                'mean_direction': np.nan, 'mean_resultant_length': np.nan}

    # Mean resultant vector
    C = np.mean(np.cos(preferred_phases))
    S = np.mean(np.sin(preferred_phases))
    R_bar = np.sqrt(C**2 + S**2)  # mean resultant length (0=uniform, 1=all same)
    mean_dir = np.arctan2(S, C)   # mean direction

    # V statistic
    V = n * R_bar * np.cos(mean_dir - expected_direction)

    # P-value via normal approximation (Zar 1999, p. 618)
    # u = V * sqrt(2/n) under H0
    u = V * np.sqrt(2.0 / n)
    p_value = 1.0 - stats.norm.cdf(u)

    return {
        'V_stat': float(V),
        'p_value': float(p_value),
        'mean_direction': float(mean_dir),
        'mean_resultant_length': float(R_bar),
    }


def cluster_permutation_test(
        group_power: np.ndarray,
        n_permutations: int = 1000,
        threshold_p: float = 0.05,
        tail: int = 1) -> np.ndarray:
    """
    Non-parametric cluster-based permutation test for TFR maps.
    Used in Staresina 2015 to identify significant time-frequency clusters.

    PRINCIPLE:
      1. Compute observed t-statistic for each time-frequency point
      2. Threshold at p < threshold_p to find candidate clusters
      3. Label connected components (clusters) in the thresholded map
      4. Compute cluster mass (sum of t-stats in each cluster)
      5. Permute signs (multiply subjects by +/-1 randomly) N times
      6. For each permutation, repeat steps 2-4, record max cluster mass
      7. Real cluster is significant if its mass > 95th percentile of null

    ANALOGY: This is like a bootstrap test but for spatial/temporal clusters.
    Like testing if a spike in your Grafana dashboard is real or noise,
    but accounting for the fact that adjacent time points are correlated.

    Parameters
    ----------
    group_power : np.ndarray (n_subjects, n_freqs, n_times)
                  Baseline-normalized power for each subject
    n_permutations : int
    threshold_p : float, p-value threshold for cluster formation
    tail : int, 1=one-tailed, 2=two-tailed

    Returns
    -------
    np.ndarray (n_freqs, n_times) bool mask: True where significant
    """
    from scipy.ndimage import label

    n_sub, n_freq, n_time = group_power.shape

    # Observed t-statistics
    t_obs, _ = stats.ttest_1samp(group_power, popmean=0, axis=0)

    # Threshold
    df = n_sub - 1
    if tail == 1:
        t_thresh = stats.t.ppf(1 - threshold_p, df)
        sig_mask_obs = t_obs > t_thresh
    else:
        t_thresh = stats.t.ppf(1 - threshold_p / 2, df)
        sig_mask_obs = np.abs(t_obs) > t_thresh

    # Observed cluster masses
    labeled, n_clusters = label(sig_mask_obs)
    if n_clusters == 0:
        return np.zeros((n_freq, n_time), dtype=bool)

    obs_cluster_masses = [
        t_obs[labeled == c + 1].sum() for c in range(n_clusters)
    ]
    max_obs_cluster = max(obs_cluster_masses) if obs_cluster_masses else 0

    # Permutation distribution of max cluster mass
    null_max_clusters = []
    for _ in range(n_permutations):
        # Random sign flip
        signs = np.random.choice([-1, 1], size=n_sub)
        perm_data = group_power * signs[:, None, None]
        t_perm, _ = stats.ttest_1samp(perm_data, popmean=0, axis=0)
        if tail == 1:
            perm_mask = t_perm > t_thresh
        else:
            perm_mask = np.abs(t_perm) > t_thresh
        lbl, n_cl = label(perm_mask)
        if n_cl > 0:
            masses = [t_perm[lbl == c + 1].sum() for c in range(n_cl)]
            null_max_clusters.append(max(masses))
        else:
            null_max_clusters.append(0.0)

    # Critical value at alpha=0.05
    critical_mass = np.percentile(null_max_clusters, 95)

    # Significant clusters
    sig_map = np.zeros((n_freq, n_time), dtype=bool)
    for c in range(n_clusters):
        if obs_cluster_masses[c] > critical_mass:
            sig_map[labeled == c + 1] = True

    return sig_map


def surrogate_contingency_test(
        so_samples: np.ndarray,
        spindle_samples: np.ndarray,
        signal_len: int,
        n_surrogates: int = 1000,
        coupling_window_s: float = 1.0,
        fs: int = 1000) -> dict:
    """
    Test whether SO-spindle temporal coupling exceeds chance.

    PRINCIPLE:
      Count how many spindles occur within coupling_window_s of an SO trough.
      Compare to surrogate distribution where spindle times are randomly
      shifted (circular shift, preserving the inter-spindle interval structure).

    Returns
    -------
    dict with 'observed_count', 'p_value', 'null_mean', 'null_std'
    """
    window = int(coupling_window_s * fs)

    def count_coupled(so_s, sp_s):
        count = 0
        for sp in sp_s:
            if np.any(np.abs(so_s - sp) <= window):
                count += 1
        return count

    observed = count_coupled(so_samples, spindle_samples)

    null_counts = []
    for _ in range(n_surrogates):
        shift = np.random.randint(1, signal_len)
        shifted = (spindle_samples + shift) % signal_len
        null_counts.append(count_coupled(so_samples, shifted))

    null_counts = np.array(null_counts)
    p_value = (null_counts >= observed).mean()

    return {
        'observed_count': int(observed),
        'p_value': float(p_value),
        'null_mean': float(null_counts.mean()),
        'null_std': float(null_counts.std()),
    }
