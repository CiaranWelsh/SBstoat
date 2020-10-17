# -*- coding: utf-8 -*-
"""
 Created on August 18, 2020

@author: joseph-hellerstein

Bootstrapping. Provides a single external: bootstrap().
Several considerations are made;
  1. Extensibility of the bootstrap results by returning
     instances of BootstrapResult.
  2. Multiprocessing. This requires a top-level (static)
     method. Arguments are packaged in _Arguments.
"""

from SBstoat.namedTimeseries import NamedTimeseries, TIME, mkNamedTimeseries
from SBstoat._bootstrapResult import BootstrapResult, COL_SUM, COL_SSQ
from SBstoat.observationSynthesizer import  \
      ObservationSynthesizerRandomizedResiduals
from SBstoat import _modelFitterCore as mfc
from SBstoat import _helpers

import lmfit
import multiprocessing
import numpy as np
import pandas as pd
import random
import typing

MAX_CHISQ_MULT = 5
PERCENTILES = [2.5, 97.55]  # Percentile for confidence limits
IS_REPORT = False
ITERATION_MULTIPLIER = 10  # Multiplier to calculate max bootsrap iterations
ITERATION_PER_PROCESS = 200  # Numer of iterations handled by a process
MAX_TRIES = 10  # Maximum number of tries to fit


###############  HELPER CLASSES ###############
class _Arguments():
    """ Arguments passed to _runBootstrap. """

    def __init__(self, fitter, numProcess:int, processIdx:int,
                 numIteration:int=10,
                 reportInterval:int=-1,
                 synthesizerClass=  \
                 ObservationSynthesizerRandomizedResiduals,
                 **kwargs: dict):
        # Same the antimony model, not roadrunner bcause of Pickle
        self.fitter = fitter.copy()
        self.numIteration  = numIteration
        self.reportInterval  = reportInterval
        self.numProcess = numProcess
        self.processIdx = processIdx
        self.synthesizerClass = synthesizerClass
        self.kwargs = kwargs
            

################# FUNCTIONS ####################
def _runBootstrap(arguments:_Arguments)->BootstrapResult:
    """
    Executes bootstrapping.

    Notes
    -----
    1. Only the first process generates progress reports.
        
    """
    # Unapack arguments
    isSuccess = False
    for _ in range(MAX_TRIES):
        try:
            fitter = arguments.fitter
            fitter.fitModel()  # Initialize model
            isSuccess = True
            break
        except:
            pass
    if not isSuccess:
        print("***Failed to fit.""")
    numIteration = arguments.numIteration
    reportInterval = arguments.reportInterval
    processIdx = arguments.processIdx
    processingRate = min(arguments.numProcess,
                         multiprocessing.cpu_count())
    synthesizer = arguments.synthesizerClass(
          observedTS=fitter.observedTS, fittedTS=fitter.fittedTS,
          **arguments.kwargs)
    # Initialize
    parameterDct = {p: [] for p in fitter.parametersToFit}
    numSuccessIteration = 0
    newObservedTS = synthesizer.calculate()
    lastReport = 0
    baseChisq = fitter.minimizerResult.redchi
    newFitter = ModelFitterBootstrap(fitter.roadrunnerModel,
          newObservedTS,  
          fitter.parametersToFit,
          selectedColumns=fitter.selectedColumns,
          method=fitter._method,
          parameterLowerBound=fitter.lowerBound,
          parameterUpperBound=fitter.upperBound,
          fittedDataTransformDct=fitter.fittedDataTransformDct,
          isPlot=fitter._isPlot)
    statisticDct = {c: newObservedTS.copy(isInitialize=True)
          for c in [COL_SUM, COL_SSQ]}
    # Do the bootstrap iterations
    for iteration in range(numIteration*ITERATION_MULTIPLIER):
        if (iteration > 0) and (numSuccessIteration != lastReport)  \
                and (processIdx == 0):
            totalIteration = numSuccessIteration*processingRate
            if totalIteration % reportInterval == 0:
                print("bootstrap completed %d iterations."
                      % totalIteration)
                lastReport = numSuccessIteration
        if numSuccessIteration >= numIteration:
            # Performed the iterations
            break
        try:
            newFitter.fitModel(params=fitter.params)
        except ValueError:
            # Problem with the fit. Don't numSuccessIteration it.
            if IS_REPORT:
                print("Fit failed on iteration %d." % iteration)
            continue
        if newFitter.minimizerResult.redchi > MAX_CHISQ_MULT*baseChisq:
            if IS_REPORT:
                print("Fit has high chisq: %2.2f on iteration %d." % iteration 
                      % newFitter.minimizerResult.redchi)
            continue
        numSuccessIteration += 1
        dct = newFitter.params.valuesdict()
        [parameterDct[p].append(dct[p]) for p in fitter.parametersToFit]
        cols = newFitter.fittedTS.colnames
        statisticDct[COL_SUM][cols] += newFitter.fittedTS[cols]
        statisticDct[COL_SSQ][cols] +=   \
              newFitter.fittedTS[cols]*newFitter.fittedTS[cols]
        newFitter.observedTS = synthesizer.calculate()
    print("Completed bootstrap process %d." % (processIdx + 1))
    return BootstrapResult(self, numSuccessIteration, parameterDct, statisticDct)


##################### CLASSES #########################
class ModelFitterBootstrap(mfc.ModelFitterCore):

    def bootstrap(self, numIteration:int=10, 
          reportInterval:int=1000,
          synthesizerClass=ObservationSynthesizerRandomizedResiduals,
          maxProcess:int=None,
          serializePath:str=None,
           **kwargs: dict):
        """
        Constructs a bootstrap estimate of parameter values.
    
        Parameters
        ----------
        numIteration: number of bootstrap iterations
        reportInterval: number of iterations between progress reports
        synthesizerClass: object that synthesizes new observations
            Must subclass ObservationSynthesizer
        maxProcess: Maximum number of processes to use. Default: numCPU
        serializePath: Where to serialize the fitter after bootstrap
        kwargs: arguments passed to ObservationSynthesizer
              
        Example
        -------
            f.bootstrap()
            f.getFittedParameters()  # Mean values
            f.getFittedParameterStds()  # Standard deviations of values

        Notes
        ----
        """
        if maxProcess is None:
            maxProcess = multiprocessing.cpu_count()
        base_redchi = self.minimizerResult.redchi
        # Run processes
        numProcess = max(int(numIteration/ITERATION_PER_PROCESS), 1)
        numProcess = min(numProcess, maxProcess)
        numProcessIteration = int(np.ceil(numIteration/numProcess))
        args_list = [_Arguments(self, numProcess, i,
              numIteration=numProcessIteration,
              reportInterval=reportInterval,
              synthesizerClass=synthesizerClass,
              **kwargs) for i in range(numProcess)]
        print("\n**Running bootstrap for %d iterations with %d processes."
              % (numIteration, numProcess))
        with multiprocessing.Pool(numProcess) as pool:
            results = pool.map(_runBootstrap, args_list)
        pool.join()
        self.bootstrapResult = BootstrapResult.merge(results)
        if serializePath is not None:
            self.serialize(serializePath)

    def getFittedParameters(self)->typing.List[float]:
        """
        Returns a list of values for fitted parameters from bootstrap.
              
        Example
        -------
              f.getFittedParameters()
        """
        if self._checkBootstrap(isError=False):
            return self.bootstrapResult.meanDct.values()
        else:
            return [self.params[p].value for p in self.parametersToFit]

    def getFittedParameterStds(self)->typing.List[float]:
        """
        Returns the standard deviations for fitted values.
              
        Example
        -------
              f.getFittedParameterStds()
        """
        self._checkBootstrap()
        return list(self.bootstrapResult.stdDct.values())

    def _checkBootstrap(self, isError:bool=True)->bool:
        """
        Verifies that bootstrap has been done.
        """
        self._checkFit()
        if self.bootstrapResult is None:
            if isError:
                raise ValueError("Must use bootstrap first.")
            else:
                return False
        return True
