# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 14:24:09 2020

@author: hsauro
@author: joseph-hellerstein

    A TimeseriesPlotter visualizes timeseries data, especially for comparing
    time series.

    All plots are line plots with the x-axis as time. The following
    can be varied:
      single or multiple columns in a plot
      one or two timeseries plot
"""

from SBstoat import _plotOptions as po
from SBstoat import _layoutManager as lm
from SBstoat.namedTimeseries import NamedTimeseries, TIME
from SBstoat._statementManager import StatementManager

import copy
from docstring_expander.expander import Expander
import matplotlib.pyplot as plt
import numpy as np
import typing


EXPAND_KEYPHRASE = "Expansion keyphrase. Expands to help(PlotOptions()). "
EXPAND_KEYPHRASE += "Do not remove. (See timeseriesPlotter.EXPAND_KEYPRHASE.)"
LABEL1 = "1"
LABEL2 = "2"
COLORS = ['r', 'g', 'b', 'c', 'pink', 'grey']
NULL_STR = ""
# Ensure lots of colors
COLORS.extend(COLORS)
COLORS.extend(COLORS)
# Title positions
POS_MID = 0.5
POS_TOP = 0.9
# Autocorrelations
MAX_LAGS = 10
NUM_STD = 2
#
IDX_PLOT1 = 0  # plot index for the first plot
IDX_PLOT2 = 1  # plot index for the second plot
DEFAULT_MARKER = "o"


########################################
class TimeseriesPlotter():

    def __init__(self, isPlot=True):
        """
        Parameters
        ---------
        isPlot: boolean
            display the plot

        Example
        -------
        plotter = TimeseriesPlotter(timeseries)
        plotter.plotTimeSingle()  # Single variable plots for one timeseries
        """
        self.isPlot = isPlot

    @staticmethod
    def _mkPlotOptionsMatrix(timeseries1, maxCol=None, **kwargs):
        """
        Creates PlotOptions for a dense matrix of plots.

        Parameters
        ----------
        timeseries1: NamedTimeseries
        isLowerTriangular: bool
            is a lower triangular matix
        maxCol: int
            maximum number of columns
        kwargs: dict

        Returns
        -------
        PlotOptions
            assigns values to options.numRow, options.numCol
        """
        options = po.PlotOptions()
        # bins
        if po.BINS in kwargs.keys():
            bins = kwargs[po.BINS]
        else:
            bins = None
        options.bins = bins
        # Second timeseries
        if po.TIMESERIES2 in kwargs.keys():
            options.timeseries2 = kwargs[po.TIMESERIES2]
        if maxCol is None:
            if po.COLUMNS in kwargs:
                maxCol = len(kwargs[po.COLUMNS])
            else:
                maxCol = len(timeseries1.colnames)
        # States
        hasRow, hasCol = TimeseriesPlotter._getOptionValueState(kwargs, options)
        # Assignments based on state
        if hasRow and hasCol:
            # Have been assigned
            pass
        elif hasRow and (not hasCol):
            options.numCol = int(maxCol/options.numRow)
        elif (not hasRow) and hasCol:
            options.numRow = int(maxCol/options.numCol)
        else:
            options.numRow = 1
            options.numCol = maxCol
        if maxCol > options.numRow*options.numCol:
            options.numRow += 1
        options.initialize(timeseries1, **kwargs)
        #
        return options

    @staticmethod
    def _getOptionValueState(kwargs, options):
        hasCol = False
        hasRow = False
        if po.NUM_ROW in kwargs:
            options.numRow = kwargs[po.NUM_ROW]
            hasRow = True
        if po.NUM_COL in kwargs:
            options.numCol = kwargs[po.NUM_COL]
            hasCol = True
        return hasRow, hasCol

    @staticmethod
    def _mkPlotOptionsLowerTriangular(timeseries1, numPlot,  **kwargs):
        """
        Creates PlotOptions for a lower triangular matrix of plots.
        2*len(pairs) - N = N**2

        Parameters
        ----------
        timeseries1: NamedTimeseries
        numPlot: int
        kwargs: dict

        Returns
        -------
        PlotOptions
            assigns values to options.numRow, options.numCol
        """
        options = po.PlotOptions()
        if numPlot == 1:
            options.numRow = 1
            options.numCol = 1
        options.initialize(timeseries1, **kwargs)
        #
        return options

    @Expander(po.KWARGS, po.BASE_OPTIONS, excludes=[po.TITLE], indent=8,
           header=po.HEADER)
    def plotTimeSingle(self, timeseries1:NamedTimeseries,
           meanTS:NamedTimeseries=None, stdTS:NamedTimeseries=None,
           bandLowTS:NamedTimeseries=None, bandHighTS:NamedTimeseries=None,
           ax_spec=None,
           position=None,  **kwargs):
        """
        Constructs plots of single columns, possibly with a second
        timeseries.

        Parameters
        ---------
        timeseries1: timeseries to plot
        meanTS: mean values of timeseries to plot
        stdTS: standard deviations of meanTS (same times)
        bandLowTS: timeseries that describes the lower band for timeseries1
        bandhighTS: timeseries that describes the higher band for timeseries1
        ax_spec: Optionally specified axis for all lines
        position: (int, int) - position of ax_spec
        #@expand

        Example
        -------
        plotter = TimeseriesPlotter()
        plotter.plotTimeSingle(timeseries)
        """
        options = TimeseriesPlotter._mkPlotOptionsMatrix(timeseries1, **kwargs)
        # Adjust rows and columns
        numPlot = len(options.columns)  # Number of plots
        if po.NUM_COL in kwargs.keys():
            options.numRow = int(np.ceil(numPlot/options.numCol))
        else:
            options.numCol = int(np.ceil(numPlot/options.numRow))
        options.set(po.XLABEL, TIME)
        # Create the LayoutManager
        if ax_spec is None:
            layout = self._mkManager(options, numPlot)
        else:
            layout = None
        #
        def mkStatement(ax, statement:StatementManager,
            timeseries:NamedTimeseries, variable:str):
            """
            Creates a plotting statement.

            Parameters
            ----------
            ax: plotting axes
            initialStatement: statement if initialized
            timeseries: what to plot
            variable: variable to plot

            Returns
            -------
            StatementManager
            """
            times, values = self._adjustSeriesForNan(
                  timeseries[TIME], timeseries[variable])
            statement.addPosarg(times)
            statement.addPosarg(values)
            return statement
        #
        def isFirstColumn(plotIdx):
            if layout is not None:
                return layout.isFirstColumn(plotIdx)
            if position is not None:
                return position[1]  == 0
            return True
        #
        def isLastRow(plotIdx):
            if layout is not None:
                return layout.isLastRow(plotIdx)
            if po.NUM_ROW in kwargs.keys():
                numRow = kwargs[po.NUM_ROW]
            else:
                return True
            if position is None:
                return True
            return position[0] + 1 == numRow
        #
        def mkBand(ts, variable, plotIdx, lineIdx):
            initialStatement = StatementManager(ax.fill_between)
            statement = mkStatement(ax, initialStatement, timeseries1, variable)
            statement.addPosarg(ts[variable])
            statement.addKwargs(alpha=0.2)
            options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
        #
        # Construct the plots
        baseOptions = copy.deepcopy(options)
        for plotIdx, variable in enumerate(options.columns):
            if ax_spec is None:
                ax = layout.getAxis(plotIdx)
            else:
                ax = ax_spec
            options = copy.deepcopy(baseOptions)
            #ax = axes[row, col]
            options.set(po.YLABEL, "concentration")
            options.set(po.TITLE, variable)
            if not isFirstColumn(plotIdx):
                options.ylabel =  NULL_STR
                options.set(po.YLABEL, "", isOverride=True)
            if not isLastRow(plotIdx):
                options.set(po.XLABEL, "", isOverride=True)
            # Construct the plot
            lineIdx = 0
            initialStatement = StatementManager(ax.plot)
            statement = mkStatement(ax, initialStatement, timeseries1, variable)
            options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
            legends = []
            if options.timeseries2 is not None:
                lineIdx = 1
                initialStatement = StatementManager(ax.plot)
                if options.marker is not None:
                    if len(options.marker) > 1:
                        if options.marker[lineIdx] is not None:
                            initialStatement = StatementManager(ax.scatter)
                    elif options.marker is not None:
                        initialStatement = StatementManager(ax.scatter)
                statement = mkStatement(ax, initialStatement,
                      options.timeseries2, variable)
                legends = [LABEL1, LABEL2]
                options.lengends = legends
                options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
            if  meanTS is not None:
                if stdTS is None:
                    stdTS = meanTS.copy(isInitialize=True)
                lineIdx = 2
                initialStatement = StatementManager(ax.scatter)
                statement = mkStatement(ax, initialStatement, meanTS, variable)
                options.marker = "^"
                statement.addKwargs(facecolors="none")
                options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
                #
                initialStatement = StatementManager(ax.errorbar)
                statement = mkStatement(ax, initialStatement, meanTS, variable)
                statement.addKwargs(yerr=stdTS[variable])
                statement.addKwargs(linestyle="none")
                legends.append("Bootstrap mean")
                options.lengends = legends
                options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
            if  bandLowTS is not None:
                lineIdx = 0
                mkBand(bandLowTS, variable, plotIdx, lineIdx)
            if  bandHighTS is not None:
                lineIdx = 0
                mkBand(bandHighTS, variable, plotIdx, lineIdx)
        if self.isPlot:
            plt.show()

    @Expander(po.KWARGS, po.BASE_OPTIONS, excludes=[po.NUM_COL, po.NUM_ROW],
          indent=8, header=po.HEADER)
    def plotTimeMultiple(self, timeseries1, **kwargs):
        """
        Constructs a plot with all columns in a timeseries.
        If there is a second timeseries, then there are 2 plots.

        Parameters
        ---------
        timeseries1: NamedTimeseries
        #@expand
        """
        numPlot = 2 if po.TIMESERIES2 in kwargs else 1
        maxCol = numPlot
        options = TimeseriesPlotter._mkPlotOptionsMatrix(timeseries1, maxCol=maxCol, **kwargs)
        if po.COLOR not in kwargs.keys():
            colors = list(COLORS)
            while len(colors) < len(timeseries1.colnames):
                colors.extend(COLORS)
            options.color = colors
        #
        def multiPlot(ax:plt.Axes, timeseries:NamedTimeseries,
              options:po.PlotOptions, plotIdx:int):
            if plotIdx == IDX_PLOT2:
                timeseries = options.timeseries2
            for lineIdx, col in enumerate(timeseries.colnames):
                if isinstance(options.marker, list):
                    marker = options.marker[lineIdx]
                else:
                    marker = options.marker
                if marker is None:
                    statement = StatementManager(ax.plot)
                else:
                    statement = StatementManager(ax.scatter)
                times, values = self._adjustSeriesForNan(
                      timeseries[TIME], timeseries[col])
                statement.addPosarg(times)
                statement.addPosarg(values)
                options.legend = timeseries.colnames
                options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
        #
        # Update rows and columns
        if options.timeseries2 is None:
            options.numRow = 1
            options.numCol = 1
        else:
            if po.NUM_ROW in kwargs:
                options.numCol = int(np.ceil(2/options.numRow))
            else:
                options.numRow = int(np.ceil(2/options.numCol))
        # Create the LayoutManager
        layout = self._mkManager(options, numPlot)
        # Construct the plots
        options.set(po.XLABEL, TIME)
        ax = layout.getAxis(0)
        multiPlot(ax, timeseries1, options, IDX_PLOT1)
        if options.timeseries2 is not None:
            ax = layout.getAxis(numPlot-1)
            multiPlot(ax, options.timeseries2, options, IDX_PLOT2)
        if self.isPlot:
            plt.show()

    def _mkManager(self, options, numPlot, isLowerTriangular=False):
        if numPlot == 1:
            layout = lm.LayoutManagerSingle(
                   options, numPlot)
        elif isLowerTriangular:
            options.set(po.TITLE_POSITION,
                (POS_MID, POS_TOP))
            layout = lm.LayoutManagerLowerTriangular(
                   options, numPlot)
        else:
            options.set(po.TITLE_POSITION,
                (POS_MID, POS_TOP))
            layout = lm.LayoutManagerMatrix(options,
                  numPlot)
        return layout

    @Expander(po.KWARGS, po.BASE_OPTIONS,
          excludes=[po.NUM_ROW, po.NUM_COL], indent=8,
          header=po.HEADER)
    def plotValuePairs(self, timeseries, pairs,
              isLowerTriangular=False, **kwargs):
        """
        Constructs plots of values of column pairs for a single
        timeseries.

        Parameters
        ---------
        timeseries: NamedTimeseries
        #@expand
        """
        numPlot = len(pairs)
        if isLowerTriangular:
            options = TimeseriesPlotter._mkPlotOptionsLowerTriangular(
                  timeseries, numPlot, **kwargs)
        else:
            options = TimeseriesPlotter._mkPlotOptionsMatrix(timeseries,
                  maxCol=numPlot, **kwargs)
        if options.marker is None:
            options.marker = DEFAULT_MARKER
        layout = self._mkManager(options, numPlot,
              isLowerTriangular=isLowerTriangular)
        options.xlabel = NULL_STR
        baseOptions = copy.deepcopy(options)
        for plotIdx, pair in enumerate(pairs):
            options = copy.deepcopy(baseOptions)
            xVar = pair[0]
            yVar = pair[1]
            ax = layout.getAxis(plotIdx)
            statement = StatementManager(ax.scatter)
            statement.addPosarg(timeseries[xVar])
            statement.addPosarg(timeseries[yVar])
            if isLowerTriangular:
                if layout.isLastRow(plotIdx):
                    options.xlabel = xVar
                else:
                    options.title = NULL_STR
                    options.xticklabels = []
                if layout.isFirstColumn(plotIdx):
                    options.ylabel = yVar
                else:
                    options.ylabel = NULL_STR
                    options.yticklabels = []
            else:
                # Matrix plot
                options.xlabel = NULL_STR
                options.ylabel = NULL_STR
                options.title = "%s v. %s" % (xVar, yVar)
            options.do(ax, statement=statement, plotIdx=plotIdx)
        if self.isPlot:
            plt.show()

    @Expander(po.KWARGS, po.BASE_OPTIONS, includes=[po.BINS], indent=8,
          header=po.HEADER)
    def plotHistograms(self, timeseries, **kwargs):
        """
        Constructs a matrix of histographs for timeseries values.

        Parameters
        ---------
        timeseries: NamedTimeseries
        #@expand
        """
        options = TimeseriesPlotter._mkPlotOptionsMatrix(timeseries, **kwargs)
        numPlot = len(options.columns)
        layout = self._mkManager(options, numPlot)
        baseOptions = copy.deepcopy(options)
        for plotIdx, column in enumerate(options.columns):
            options = copy.deepcopy(baseOptions)
            ax = layout.getAxis(plotIdx)
            if layout.isFirstColumn(plotIdx):
                options.ylabel = "density"
            if not layout.isFirstColumn(plotIdx):
                options.ylabel = NULL_STR
            if layout.isLastRow(plotIdx):
                options.xlabel = "value"
            else:
                options.xlabel = NULL_STR
            # Matrix plot
            options.title = column
            statement = StatementManager(ax.hist)
            statement.addPosarg(timeseries[column])
            statement.addKwargs(density=True)
            if options.bins is not None:
                statement.addKwargs(bins=options.bins)
            options.do(ax, statement=statement, plotIdx=plotIdx)
        if self.isPlot:
            plt.show()

    @Expander(po.KWARGS, po.BASE_OPTIONS, indent=8,
          header=po.HEADER)
    def plotCompare(self,
           ts1: NamedTimeseries,
           ts2: NamedTimeseries,
           **kwargs: dict):
        """
        Plots columns against each other.

        Parameters
        ----------
        #@expand
        """
        mergedTS = ts1.concatenateColumns(ts2)
        pairs = [(c, "%s_" % c) for c in ts1.colnames]
        #
        self.plotValuePairs(mergedTS, pairs, **kwargs)

    def _mkAutocorrelation(self, timeseries:NamedTimeseries, numPlot:int=None,
          isLowerTriangular:bool=False, **kwargs:dict)  \
          -> typing.Tuple[po.PlotOptions, lm.LayoutManager]:
        """
        Constructs options and layout for autocorrelation plots.
        """
        if isLowerTriangular:
            options = TimeseriesPlotter._mkPlotOptionsLowerTriangular(
                  timeseries, numPlot, **kwargs)
        else:
            options = TimeseriesPlotter._mkPlotOptionsMatrix(timeseries, **kwargs)
            numPlot = len(options.columns)
        layout = self._mkManager(options, numPlot,
              isLowerTriangular=isLowerTriangular)
        options.set(po.XLABEL, "lag")
        options.set(po.YLABEL, "autocorrelation")
        options.set(po.YLIM, [-1.2, 1.2])
        return options, layout

    def _mkAutocorrelationErrorBounds(self, timeseries:NamedTimeseries)  \
          -> typing.Tuple[typing.List[int], typing.List[float], typing.List[float]]:
        def mkFullArray(arr):
            reverse_arr = arr[::-1]
            return np.concatenate([reverse_arr, arr[1:]])
        # Construct lags
        upper_lags = np.array(range(1, MAX_LAGS+1))
        lower_lags = -1*upper_lags
        lower_lags.sort()
        lags = np.concatenate([lower_lags, np.array([0]), upper_lags])
        #
        length = len(timeseries)
        upper_line = np.array([NUM_STD/(np.sqrt(length - l))
              for l in range(MAX_LAGS+1)])
        lower_line = -1*upper_line
        upper_line = mkFullArray(upper_line)
        lower_line = mkFullArray(lower_line)
        #
        return lags, lower_line, upper_line

    @Expander(po.KWARGS, po.BASE_OPTIONS, indent=8,
          header=po.HEADER)
    def plotAutoCorrelations(self, timeseries:NamedTimeseries,
           **kwargs:dict):
        """
        Plots autocorrelations for a timeseries.
        Uses the Barlet bound to estimate confidence intervals.

        Parameters
        ----------
        #@expand
        """
        # Structure the plots
        baseOptions, layout = self._mkAutocorrelation(timeseries,
              isLowerTriangular=False, **kwargs)
        lags, lower_line, upper_line = self._mkAutocorrelationErrorBounds(timeseries)
        baseOptions.set(po.SUPTITLE, "Autocorrelations")
        for plotIdx, column in enumerate(baseOptions.columns):
            options = copy.deepcopy(baseOptions)
            ax = layout.getAxis(plotIdx)
            if not layout.isFirstColumn(plotIdx):
                options.ylabel = NULL_STR
            if not layout.isLastRow(plotIdx):
                options.xlabel = NULL_STR
            # Matrix plot
            lineIdx = 0
            options.title = column
            statement = StatementManager(ax.acorr)
            statement.addPosarg(timeseries[column])
            statement.addKwargs(maxlags=MAX_LAGS)
            options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
            #
            self._addConfidenceLines(ax, lags, [lower_line, upper_line], options,
                  lineIdx, plotIdx=plotIdx)
        if self.isPlot:
            plt.show()

    def _addConfidenceLines(self, ax, xline, lines, options, startLineIdx, **kwargs):
        lineIdx = startLineIdx
        for line in lines:
            lineIdx += 1
            statement = StatementManager(ax.plot)
            statement.addPosarg(xline)
            statement.addPosarg(line)
            options.do(ax, statement=statement, lineIdx=lineIdx, **kwargs)

    @Expander(po.KWARGS, po.BASE_OPTIONS, indent=8,
          header=po.HEADER)
    def plotCrossCorrelations(self, timeseries:NamedTimeseries,
          **kwargs:dict):
        """
        Constructs pairs of cross correlation plots.
        Uses the Barlet bound to estimate confidence intervals.

        Parameters
        ----------
        #@expand
        """
        if po.COLUMNS in kwargs.keys():
            numCol = len(po.COLUMNS)
        else:
            numCol = len(timeseries.colnames)
        numPlot = int((numCol**2 - numCol)/2)
        baseOptions, layout = self._mkAutocorrelation(timeseries,
              numPlot=numPlot, isLowerTriangular=True, **kwargs)
        # Construct the plot pairs
        pairs = []
        columns = list(baseOptions.columns)
        for col1 in baseOptions.columns:
            columns.remove(col1)
            for col2 in columns:
                pairs.append((col1, col2))
        lags, lower_line, upper_line = self._mkAutocorrelationErrorBounds(
              timeseries)
        baseOptions.set(po.SUPTITLE, "Cross Correlations")
        # Do the plots
        for plotIdx, pair in enumerate(pairs):
            options = copy.deepcopy(baseOptions)
            xVar = pair[0]
            yVar = pair[1]
            options.set(po.TITLE, "%s, %s" % (xVar, yVar))
            ax = layout.getAxis(plotIdx)
            if layout.isLastRow(plotIdx):
                options.xlabel = "lag"
            else:
                options.xticklabels = []
            if layout.isFirstColumn(plotIdx):
                options.ylabel = "corr"
            else:
                options.ylabel = NULL_STR
                options.yticklabels = []
            # Matrix plot
            lineIdx = 0
            statement = StatementManager(ax.xcorr)
            statement.addPosarg(timeseries[xVar])
            statement.addPosarg(timeseries[yVar])
            statement.addKwargs(maxlags=MAX_LAGS)
            options.do(ax, statement=statement, plotIdx=plotIdx, lineIdx=lineIdx)
            self._addConfidenceLines(ax, lags, [lower_line, upper_line], options,
                  lineIdx, plotIdx=plotIdx)
        if self.isPlot:
            plt.show()

    def _adjustSeriesForNan(self, times, values):
        indices = [i for i in range(len(values)) if not np.isnan(values[i])]
        return times[indices], values[indices]
