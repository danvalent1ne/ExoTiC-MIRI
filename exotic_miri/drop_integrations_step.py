import numpy as np
from jwst import datamodels
from jwst.stpipe import Step


class DropIntegrationsStep(Step):
    """ Drop integrations within data chunk.

    This steps allows you to drop integrations from a data chunk
    owing to these groups being too severely affected by systematics.
    This step may also be useful if wanting to test pipelines on
    only a small subset of data.

    """

    spec = """
    integrations = int_list()  #  integrations to drop, zero-indexed.
    """

    def process(self, input):
        """Execute the step.

        Parameters
        ----------
        input: JWST data model
            A data model of type RampModel.

        Returns
        -------
        JWST data model
            A RampModel with updated integrations, unless the
            step is skipped in which case `input_model` is returned.
        """
        with datamodels.open(input) as input_model:

            # Copy input model.
            thinned_model = input_model.copy()

            # Check input model type.
            if not isinstance(input_model, datamodels.RampModel):
                self.log.error('Input is a {} which was not expected for _int'
                               'egrations_step, skipping step.'.format(
                                str(type(input_model))))
                thinned_model.meta.cal_step.drop_integrations = 'SKIPPED'
                return thinned_model

            # Check the observation mode.
            if not input_model.meta.exposure.type == 'MIR_LRS-SLITLESS':
                self.log.error('Observation is a {} which is not supported by'
                               ' ExoTic-MIRIs drop_integrations_step, skippin'
                               'g step.'.format(
                                input_model.meta.exposure.type))
                thinned_model.meta.cal_step.drop_integrations = 'SKIPPED'
                return thinned_model

            # Check integrations to drop exist within data chunk.
            min_i_drop = np.min(self.integrations)
            max_i_drop = np.max(self.integrations)
            current_n_integrations = thinned_model.data.shape[0]
            if min_i_drop < 0 or max_i_drop > current_n_integrations - 1:
                self.log.error('Not all integrations listed for dropping exis'
                               't, requested to drop integrations between {} '
                               'and {} when current integrations only span 0 '
                               'to {}. Check your input list is zero indexed,'
                               ' skipping step.'.format(
                                min_i_drop, max_i_drop,
                                current_n_integrations - 1))
                thinned_model.meta.cal_step.drop_integrations = 'SKIPPED'
                return thinned_model

            # Compute wanted integrations.
            current_integrations = np.arange(0, current_n_integrations, 1)
            wanted_integrations = current_integrations[~np.isin(
                current_integrations, self.integrations)]

            # Drop integrations.
            thinned_model.data = thinned_model.data[
                                 wanted_integrations, :, :, :]
            thinned_model.err = thinned_model.err[
                                wanted_integrations, :, :, :]
            thinned_model.groupdq = thinned_model.groupdq[
                                    wanted_integrations, :, :, :]

            # Update meta.
            thinned_model.meta.nints = thinned_model.data.shape[0]
            thinned_model.meta.nints_file = thinned_model.data.shape[0]
            thinned_model.meta.exposure.nints = thinned_model.data.shape[0]

        return thinned_model
