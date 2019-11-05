"""
==============================================================================
Compute iterative reweighted TF-MxNE with multiscale time-frequency dictionary
==============================================================================

The iterative reweighted TF-MxNE solver is a distributed inverse method
based on the TF-MxNE solver, which promotes focal (sparse) sources.
[1]_. The benefit of this approach is that:

  - it is spatio-temporal without assuming stationarity (sources properties
    can vary over time)
  - activations are localized in space, time and frequency in one step.
  - the solver uses non-convex penalties in the TF domain, which result in
    solution less biased towards zero than when simple TF-MxNE is used.

References
----------
.. [1] D. Strohmeier, Y. Bekhti, J. Haueisen, A. Gramfort
   "The iterative reweighted Mixed-Norm Estimate for spatio-temporal MEG/EEG
   source reconstruction",
   IEEE transactions on medical imaging, 35(10), 2218-2228.
   DOI: 10.1109/TMI.2016.2553445
"""
# Author: Mathurin Massias <mathurin.massias@gmail.com>
#
# License: BSD (3-clause)

from os.path import join as pjoin

import mne
from mne.datasets import somato
from mne.inverse_sparse import tf_mixed_norm, make_stc_from_dipoles
from mne.viz import plot_sparse_source_estimates

print(__doc__)


###############################################################################
# Load somatosensory MEG data

data_path = somato.data_path()
subjects_dir = pjoin(data_path, 'subjects')
raw_fname = pjoin(data_path, 'MEG', 'somato', 'sef_raw_sss.fif')
fwd_fname = pjoin(data_path, 'MEG', 'somato', 'somato-meg-oct-6-fwd.fif')

condition = 'Unknown'

# Read evoked
raw = mne.io.read_raw_fif(raw_fname)
events = mne.find_events(raw, stim_channel='STI 014')
reject = dict(grad=4000e-13, eog=150e-6)
picks = mne.pick_types(raw.info, meg=True, eog=True)

event_id, tmin, tmax = 1, -1., 3.
baseline = (None, 0)
epochs = mne.Epochs(raw, events, event_id, tmin, tmax, picks=picks,
                    baseline=baseline, reject=reject, preload=True)
evoked = epochs.average()
evoked = evoked.pick_types(meg=True)
evoked.crop(tmin=-0.05, tmax=0.35)

# Compute noise covariance matrix
cov = mne.compute_covariance(epochs, tmax=0.)

# Handling forward solution
forward = mne.read_forward_solution(fwd_fname)

###############################################################################
# Run iterative reweighted multidict TFMxNE solvers

alpha, l1_ratio = 35, 0.002
loose, depth = 0.2, 0.9
# Use a multiscale time-frequency dictionary
wsize, tstep = [16, 64], [2, 4]


n_tfmxne_iter = 5
# Compute TF-MxNE inverse solution with dipole output
dipoles, residual = tf_mixed_norm(
    evoked, forward, cov, alpha=alpha, l1_ratio=l1_ratio,
    n_tfmxne_iter=n_tfmxne_iter, loose=loose,
    depth=depth,
    wsize=wsize, tstep=tstep, return_as_dipoles=True,
    return_residual=True)

# Crop to remove edges
for dip in dipoles:
    dip.crop(tmin=0., tmax=0.3)
evoked.crop(tmin=0., tmax=0.3)
residual.crop(tmin=0., tmax=0.3)


###############################################################################
# Generate stc from dipoles
stc = make_stc_from_dipoles(dipoles, forward['src'])

plot_sparse_source_estimates(forward['src'], stc, bgcolor=(1, 1, 1),
                             opacity=0.1, fig_name="irTF-MxNE (cond %s)"
                             % condition, modes=['sphere'], scale_factors=[1.])


###############################################################################
# Show the evoked response and the residual for gradiometers
ylim = dict(grad=[-300, 300])
evoked.pick_types(meg='grad', exclude='bads')
evoked.plot(titles=dict(grad='Evoked Response: Gradiometers'), ylim=ylim,
            proj=True)

residual.pick_types(meg='grad', exclude='bads')
residual.plot(titles=dict(grad='Residuals: Gradiometers'), ylim=ylim,
              proj=True)
