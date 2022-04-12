import os
import pickle
import unittest
import numpy as np
import matplotlib.pyplot as plt

os.environ['CRDS_PATH'] = 'crds_cache'
os.environ['CRDS_SERVER_URL'] = 'https://jwst-crds.stsci.edu'

from jwst import datamodels

from exotic_miri import Extract1dStep
from jwst import gain_scale


class TestExtract1d(unittest.TestCase):
    """ Test extract 1d step. """

    def __init__(self, *args, **kwargs):
        super(TestExtract1d, self).__init__(*args, **kwargs)

        # Synthesise test data.
        self.spec_trace_signal_amp = 1.5e6
        inj, sci, err = self._make_miri_ish_data_chunk(draw=False)
        self.ground_truth_spectra = inj

        # Build test CubeModel data structure.
        self.test_cube_model = datamodels.CubeModel()
        self.test_cube_model.data = sci
        self.test_cube_model.err = err
        self.test_cube_model.groupdq = np.zeros((100, 416, 72))
        self.test_cube_model.pixeldq = np.zeros((416, 72))
        self.test_cube_model.meta.ngroups = 50
        self.test_cube_model.meta.ngroups_file = 50
        self.test_cube_model.meta.nints = 1000
        self.test_cube_model.meta.nints_file = 1000
        self.test_cube_model.meta.exposure.integration_time = 10.3376
        self.test_cube_model.meta.exposure.ngroups = 50
        self.test_cube_model.meta.exposure.nints = 1000
        self.test_cube_model.meta.exposure.type = 'MIR_LRS-SLITLESS'
        self.test_cube_model.meta.exposure.readpatt = 'FASTR1'
        self.test_cube_model.meta.instrument.name = 'MIRI'
        self.test_cube_model.meta.instrument.detector = 'MIRIMAGE'
        self.test_cube_model.meta.observation.date = '2022-01-01'
        self.test_cube_model.meta.observation.time = '17:00:00'
        self.test_cube_model.meta.subarray.name = 'SLITLESSPRISM'
        self.test_cube_model.meta.subarray.xsize = 72
        self.test_cube_model.meta.subarray.xstart = 1
        self.test_cube_model.meta.subarray.ysize = 416
        self.test_cube_model.meta.subarray.ystart = 529
        self.test_cube_model.meta.bunit_data = 'DN/S'
        self.test_cube_model.meta.model_type = 'CubeModel'
        self._set_wcs_from_pickle('jar/test_wcs.p')

    def _set_wcs_from_pickle(self, pickle_path):
        """ Set meta data associated with wcs. """
        with open(pickle_path, 'rb') as p:
            wcs_obj = pickle.load(p)
            self.test_cube_model.meta.wcs = wcs_obj

        self.test_cube_model.meta.wcsinfo.cdelt1 = 1.0
        self.test_cube_model.meta.wcsinfo.cdelt2 = 1.0
        self.test_cube_model.meta.wcsinfo.cdelt3 = 1.0
        self.test_cube_model.meta.wcsinfo.crpix1 = 0
        self.test_cube_model.meta.wcsinfo.crpix2 = -528
        self.test_cube_model.meta.wcsinfo.crpix3 = 0
        self.test_cube_model.meta.wcsinfo.crval1 = 0.0
        self.test_cube_model.meta.wcsinfo.crval2 = 0.0
        self.test_cube_model.meta.wcsinfo.crval3 = 0.0
        self.test_cube_model.meta.wcsinfo.ctype1 = None
        self.test_cube_model.meta.wcsinfo.ctype2 = None
        self.test_cube_model.meta.wcsinfo.ctype3 = None
        self.test_cube_model.meta.wcsinfo.cunit1 = None
        self.test_cube_model.meta.wcsinfo.cunit2 = None
        self.test_cube_model.meta.wcsinfo.cunit3 = None
        self.test_cube_model.meta.wcsinfo.dec_ref = 0.0
        self.test_cube_model.meta.wcsinfo.ra_ref = 0.0
        self.test_cube_model.meta.wcsinfo.roll_ref = -0.0
        self.test_cube_model.meta.wcsinfo.v2_ref = -378.8320736785982
        self.test_cube_model.meta.wcsinfo.v3_ref = -344.9445433053003
        self.test_cube_model.meta.wcsinfo.v3yangle = 0.0
        self.test_cube_model.meta.wcsinfo.vparity = -1
        self.test_cube_model.meta.wcsinfo.wcsaxes = 3

    def _make_miri_ish_data_chunk(self, draw=False):
        """ Synthesise some MIRI-ish data. """
        np.random.seed(111)
        n_rows = 416
        n_cols = 72
        n_ints = 100
        row_pixel_vals = np.arange(0, n_rows)
        col_pixel_vals = np.arange(0, n_cols)

        # Shifting spectral trace.
        psf_locs = np.linspace(35.5, 36.5, n_ints) \
                   + np.random.normal(loc=0., scale=0.00001, size=n_ints)
        psf_sigmas = np.linspace(1.31, 1.35, n_rows)
        spec_trace_sigma = 75.
        spec_trace_locs = np.linspace(210.5, 211.5, n_ints) \
                          + np.random.normal(loc=0., scale=0.00001, size=n_ints)

        # Data arrays: bkg, science, err, read noise, and gain.
        integration_time = 10.3376
        bkg = 1000. * np.ones((n_rows, n_cols)) \
              * np.linspace(0.98, 1.02, n_rows)[:, np.newaxis]
        sci = np.zeros((n_rows, n_cols))
        err = np.zeros((n_rows, n_cols))
        rn = np.random.normal(loc=.0, scale=5., size=(n_rows, n_cols))
        gain = 5.5 * np.ones((n_rows, n_cols))

        # Generate integrations.
        injections = []
        integrations = []
        errors = []
        for i in range(n_ints):

            # Build psf.
            int_sci = np.zeros(sci.shape)
            for row_idx in row_pixel_vals:
                int_sci[row_idx] = self._gaussian(
                    col_pixel_vals, psf_locs[i], psf_sigmas[row_idx])

            # Build spectral trace.
            spec_trace = self._gaussian(
                row_pixel_vals, spec_trace_locs[i], spec_trace_sigma)
            int_sci *= spec_trace[:, np.newaxis]

            # Add signal.
            int_sci *= self.spec_trace_signal_amp
            injections.append(np.sum(int_sci / gain, axis=1))
            int_sci += bkg
            int_sci += rn
            int_sci_dn = np.random.poisson(int_sci) / gain
            int_err_dn = (rn**2 + np.abs(int_sci_dn) / gain)**0.5

            # Convert to rate units.
            int_sci_dn_per_s = int_sci_dn / integration_time
            int_err_dn_per_s = int_err_dn / integration_time

            integrations.append(int_sci_dn_per_s)
            errors.append(int_err_dn_per_s)

            if draw:
                fig = plt.figure(figsize=(8, 7))
                ax1 = fig.add_subplot(111, projection='3d')
                xx, yy = np.meshgrid(col_pixel_vals, row_pixel_vals)
                ax1.plot_surface(xx, yy, int_sci, cmap='cividis',
                                 lw=0., rstride=1, cstride=1, alpha=0.9)
                ax1.set_xlabel('Pixel column')
                ax1.set_ylabel('Pixel row')
                ax1.set_zlabel('DN/s')
                plt.show()

        return np.array(injections), np.array(integrations), np.array(errors)

    def _gaussian(self, x_vals, mu, sigma):
        """ Gaussian/normal distribution function. """
        y = 1 / (sigma * (2 * np.pi) ** 0.5) * np.exp(
            -(x_vals - mu) ** 2 / (2. * sigma ** 2))
        return y

    def test_extract_1d_bkg_const_spec_box(self):
        """ Test the extract 1d step: bkg=const, spec=box. """
        spectral_model = Extract1dStep().call(
            self.test_cube_model,
            bkg_region=[8, 22, 52, 70],
            bkg_algo='constant',
            bkg_poly_order=0,
            bkg_smoothing_length=50,
            extract_region_width=19,
            extract_algo='anchor',
            extract_poly_order=8,
            max_iter=10)

        # White light plots.
        lc_injected = []
        lc_observed = []
        for ii in range(len(spectral_model.spectra)):
            lc_injected.append(self.ground_truth_spectra[ii].sum())
            lc_observed.append(spectral_model.spectra[ii]['flux'].sum())
        lc_injected = np.array(lc_injected)
        lc_injected /= np.median(lc_injected)
        lc_observed = np.array(lc_observed)
        lc_observed /= np.median(lc_observed)

        print(np.std(lc_observed - lc_injected))
        plt.scatter(np.arange(100), lc_observed)
        plt.scatter(np.arange(100), lc_injected)
        plt.show()

        # Todo: if enforce +ve in entire axis then divide by zero.

        # Todo: add new method option.
        # Todo: add methods for different options.
        # Todo: add asseetions.

        # Check if recover the injected spectra.
        for idx_int in range(len(spectral_model.spectra)):
            recovered_spec = spectral_model.spectra[idx_int]['flux']
            recovered_sigma = spectral_model.spectra[idx_int]['flux_error']
            residuals = recovered_spec - self.ground_truth_spectra[idx_int]
            deviations = np.abs(residuals) / recovered_sigma
            self.assertLess(np.max(deviations), 10.)


if __name__ == '__main__':
    unittest.main()
