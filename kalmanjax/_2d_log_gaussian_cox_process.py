import numpy as np
from jax.experimental import optimizers
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb, rgb_to_hsv, ListedColormap
from scipy.interpolate import interp1d
import time
from sde_gp import SDEGP
import approximate_inference as approx_inf
import priors
import likelihoods
from utils import softplus_list, discretegrid
pi = 3.141592653589793

plot_intermediate = False

print('loading rainforest data ...')
data = np.loadtxt('../data/TRI2TU-data.csv', delimiter=',')

nr = 50  # spatial grid point (y-aixs)
nt = 100  # temporal grid points (x-axis)
# scale = 1000 / nt

t, r, Y = discretegrid(data, [0, 1000, 0, 500], [nt, nr])

# Ttest, Rtest = np.mgrid[0:1000:100j, 0:500:50j]

np.random.seed(99)
N = nr * nt  # number of data points

var_f = 0.5  # GP variance
len_f = 12  # lengthscale

prior = priors.SpatialMatern52(variance=var_f, lengthscale=len_f, z=r[0, ...], fixed_grid=True)
lik = likelihoods.Poisson()
inf_method = approx_inf.ExtendedKalmanSmoother(damping=0.5)
# inf_method = approx_inf.ExtendedEP()

# t_spacetime = np.block([t[..., 0][..., None], r])

model = SDEGP(prior=prior, likelihood=lik, x=t, y=Y, r=r, x_test=t, y_test=Y, r_test=r, approx_inf=inf_method)

opt_init, opt_update, get_params = optimizers.adam(step_size=1e-1)
# parameters should be a 2-element list [param_prior, param_likelihood]
opt_state = opt_init([model.prior.hyp, model.likelihood.hyp])


def gradient_step(i, state, mod, plot_num_, mu_prev_):
    params = get_params(state)
    mod.prior.hyp = params[0]
    mod.likelihood.hyp = params[1]

    # grad(Filter) + Smoother:
    neg_log_marg_lik, gradients = mod.run()
    # neg_log_marg_lik, gradients = mod.run_two_stage()  # <-- less elegant but reduces compile time

    prior_params = softplus_list(params[0])
    print('iter %2d: var=%1.2f len=%1.2f, nlml=%2.2f' %
          (i, prior_params[0], prior_params[1], neg_log_marg_lik))

    return opt_update(i, gradients, state), plot_num_, mu_prev_


plot_num = 0
mu_prev = None
print('optimising the hyperparameters ...')
t0 = time.time()
for j in range(2):
    opt_state, plot_num, mu_prev = gradient_step(j, opt_state, model, plot_num, mu_prev)
t1 = time.time()
print('optimisation time: %2.2f secs' % (t1-t0))

# calculate posterior predictive distribution via filtering and smoothing at train & test locations:
print('calculating the posterior predictive distribution ...')
t0 = time.time()
# posterior_mean, posterior_cov, _, nlpd = model.predict()
mu, var, _, nlpd_test, _, _ = model.predict_2d()
mu = np.squeeze(mu)
t1 = time.time()
print('prediction time: %2.2f secs' % (t1-t0))
# print('test NLPD: %1.2f' % nlpd)

# lb = posterior_mean[:, 0, 0] - 1.96 * posterior_cov[:, 0, 0] ** 0.5
# ub = posterior_mean[:, 0, 0] + 1.96 * posterior_cov[:, 0, 0] ** 0.5
# x_pred = model.t_all
# test_id = model.test_id
link_fn = model.likelihood.link_fn

# print('sampling from the posterior ...')
# t0 = time.time()
# posterior_samp = model.posterior_sample(20)
# t1 = time.time()
# print('sampling time: %2.2f secs' % (t1-t0))

print('plotting ...')
# plt.figure(1)
# for label, mark in [[1, 'o'], [0, 'o']]:
#     ind = Y[:, 0] == label
#     # ax.plot(X[ind, 0], X[ind, 1], mark)
#     plt.scatter(X[ind, 0], X[ind, 1], s=50, alpha=.5)
# # ax.imshow(mu.T)
# plt.contour(Xtest, Ytest, mu, levels=[.0], colors='k', linewidths=4.)
# # plt.axis('equal')
# plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
# plt.tick_params(axis='y', which='both', right=False, left=False, labelleft=False)
# # ax.axis('off')
# lim = 2.8
# plt.xlim(-lim, lim)
# plt.ylim(-lim, lim)
# plt.savefig('output/data.png')

# x1 = np.linspace(-lim, lim, num=100)
# x2 = np.linspace(-lim, lim, num=100)
# cmap_ = [[1, 0.498039215686275, 0.0549019607843137], [0.12156862745098, 0.466666666666667, 0.705882352941177]]
# cmap = hsv_to_rgb(interp1d([-0.5, 20.], rgb_to_hsv(cmap_), axis=0)(np.linspace(-0.5, 20, num=64)))
# newcmp = ListedColormap(cmap)

plt.figure(1, figsize=(10, 5))
# im = plt.imshow(mu.T, cmap=newcmp, extent=[0, 1000, 0, 500], origin='lower')
im = plt.imshow(mu.T, extent=[0, 1000, 0, 500], origin='lower')
# im = plt.imshow(link_fn(mu).T / scale, extent=[0, 1000, 0, 500], origin='lower')
# cb = plt.colorbar(im)
plt.colorbar(im, fraction=0.0235, pad=0.04)
# cb.set_ticks([cb.vmin, 0, cb.vmax])
# cb.set_ticklabels([-1, 0, 1])
# plt.contour(Xtest, Ytest, mu, levels=[.0], colors='k', linewidths=1.5)
# plt.axis('equal')
# for label in [1, 0]:
#     ind = Y[:, 0] == label
#     plt.scatter(X[ind, 0], X[ind, 1], s=50, alpha=.5, edgecolor='k')
# plt.title('Iteration: %02d' % (j + 1), loc='right', fontweight='bold')
# plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
# plt.tick_params(axis='y', which='both', right=False, left=False, labelleft=False)
plt.xlim(0, 1000)
plt.ylim(0, 500)
plt.title('2D log-Gaussian Cox process (rainforest tree data). Log-intensity shown.')
plt.xlabel('first spatial dimension, $t$ (metres)')
plt.ylabel('second spatial dimension, $r$ (metres)')
# plt.savefig('output/output_%04d.png' % 1600)
plt.show()
