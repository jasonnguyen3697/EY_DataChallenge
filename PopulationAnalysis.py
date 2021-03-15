# -*- coding: utf-8 -*-
"""
@author: An Binh (Jason) Nguyen
@date: 14/03/2021
@introduction: Optimmisations around ED wait time and staffing are highly desireable in a world where detailed records of patience visits are kept by hospitals.
@purpose: This script generates and analyses two populations of interest:
            1. Where Arrival time - Dr seen time are within ATS's guidelines
            2. Where Arrival time - Dr seen time exceed ATS's guidelines
          The analyses attempts to understand the possible reasons for tardiness in patient inspections, and guide proposed solutions
"""
import pandas as pd
import scipy.stats as stats
from sklearn import linear_model
import statsmodels.api as sm
import statsmodels.stats as sm_stats
import statsmodels.formula.api as sm_formula
import numpy as np

def summariseTukeyTest(tukeydf, factor):
    """Function to analyse tukey test result. Assume group values start at 1.
    """
    uniqueValues = list(set(list(tukeydf["group1"]) + list(tukeydf["group2"])))
    tukeySummaryDf = pd.DataFrame({factor: uniqueValues, "StatisticallySignificantInstance": [0 for i in range(len(uniqueValues))], "Better": [0 for i in range(len(uniqueValues))], "Worse": [0 for i in range(len(uniqueValues))]})
    
    # filter only for reject = True
    tukeyTrue = tukeydf.loc[tukeydf["reject"]].reset_index(drop=True)
    
    for i in range(len(tukeyTrue)):
        group1 = tukeyTrue.iloc[i]["group1"]
        group2 = tukeyTrue.iloc[i]["group2"]
        tukeySummaryDf.loc[tukeySummaryDf["group1"]==group1, "StatisticallySignificantInstance"] += 1
        tukeySummaryDf.loc[tukeySummaryDf["group2"]==group2, "StatisticallySignificantInstance"] += 1
        if tukeyTrue.iloc[i]["meandiff"] < 0:
            tukeySummaryDf.loc[tukeySummaryDf["group1"]==group1, "Worse"] += 1
            tukeySummaryDf.loc[tukeySummaryDf["group2"]==group2, "Better"] += 1
        else:
            tukeySummaryDf.loc[tukeySummaryDf["group1"]==group1, "Better"] += 1
            tukeySummaryDf.loc[tukeySummaryDf["group2"]==group2, "Worse"] += 1
            
    tukeySummaryDf = pd.DataFrame(tukeySummaryDf)
    
    return tukeySummaryDf

# read dataset and timeline
transformedDataset = pd.read_excel("output.xlsx", sheet_name="Dataset_ED_transformed")
presentationTimeline = pd.read_excel("output.xlsx", sheet_name="Presentation Timeline")

# rename columns
transformedDataset.rename(columns={"Triage Priority": "TriagePriority", "Arrival Month": "ArrivalMonth", "Arrival Day Of Week": "ArrivalDayOfWeek", "TimeDiff Arrival-TreatDrNr (mins)": "TimeDiffArrival_TreatDrNr_mins", " Age  (yrs)": "Age (years)"}, inplace=True)

# analyse population segmented by TreatedLaterThanOrdering flag
print("Analyse population segmented by TreatedLaterThanOrdering flag")
TreatedLaterThanOrdering_0 = transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==0) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"]
TreatedLaterThanOrdering_1 = transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==1) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"]

print("--- Test for distribution normality")
# test assumption that LateSeenByDr is a normal distr
normTest_0 = stats.shapiro(TreatedLaterThanOrdering_0)
normTest_1 = stats.shapiro(TreatedLaterThanOrdering_1)

# assume normality
if (normTest_0[1] >= 0.05) and (normTest_1[1] >= 0.05):
    # t-test for TreatedLaterThanOrdering
    print("--- Normality test passed")
    res = stats.ttest_ind(transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==0) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"], transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==1) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"], equal_var=False)
    if res.pvalue < 0.05:
        print("--- P-value: {}\nStatiscally significant!".format(res.pvalue))
else:
    print("--- Normality test failed, use Mann Whitney U test")
    # test for distribution median difference significance
    # use Mann Whitney test
    mannWhitneyU = stats.mannwhitneyu(TreatedLaterThanOrdering_0, TreatedLaterThanOrdering_1)
    if mannWhitneyU[1] < 0.05:
        print("--- P-value: {}\nStatistically significant!".format(mannWhitneyU[1]))
        
    # mean rank calculation
    populationRank = transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["LateSeenByDr", "TreatedLaterThanOrdering"]]
    populationRank['Rank'] = populationRank["LateSeenByDr"].rank(method='average')
    sumRank_0 = populationRank.loc[populationRank["TreatedLaterThanOrdering"]==0]["Rank"].sum()
    meanRank_0 = sumRank_0/(len(populationRank.loc[populationRank["TreatedLaterThanOrdering"]==0]))
    sumRank_1 = populationRank.loc[populationRank["TreatedLaterThanOrdering"]==1]["Rank"].sum()
    meanRank_1 = sumRank_1/(len(populationRank.loc[populationRank["TreatedLaterThanOrdering"]==1]))
    
    SumMeanRankTable = pd.DataFrame({"TreatedLaterThanOrdering": [0, 1], "Mean rank": [meanRank_0, meanRank_1]})
    
    print("Mean rank table")
    print(SumMeanRankTable)

# graph density for TreatedLaterThanOrdering and LateSeenByDr
ax = transformedDataset[["TreatedLaterThanOrdering", "LateSeenByDr"]].pivot(columns="TreatedLaterThanOrdering", values="LateSeenByDr").plot.density(alpha=0.5, figsize=(15, 12))

# multi-factor linear regression
# calculate accepatable range
mean = transformedDataset["LateSeenByDr"].mean()
threeStd = transformedDataset["LateSeenByDr"].std() * 3
lowerBound = mean - threeStd
upperBound = mean + threeStd

## using scikit-learn
#reg = linear_model.LinearRegression()
#reg.fit(transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["TriagePriority"]], transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()]["LateSeenByDr"])
#
## calculate r2 of model
#r2 = reg.score(transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["Triage 1 count", "Triage 2 count", "Triage 3 count", "Triage 4 count", "Triage 5 count"]], transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()]["LateSeenByDr"])

# using statsmodel
est = sm.OLS(transformedDataset.loc[(~transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["LateSeenByDr"], transformedDataset.loc[(~transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)][["Triage 1 count", "Triage 2 count", "Triage 3 count", "Triage 4 count", "Triage 5 count"]])

est = est.fit()

print(est.summary())

# calculate statistical significance of ArrivalMonth, and ArrivalDayOfWeek
formula = "LateSeenByDr ~ C(ArrivalMonth) + C(ArrivalDayOfWeek)"
lm = sm_formula.ols(formula, transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]).fit()
print(lm.summary())

# perform Tukey test for ArrivalMonth
tukeyMonth = sm_stats.multicomp.pairwise_tukeyhsd(transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["LateSeenByDr"], transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["ArrivalMonth"])

tukeyResultsMonth = pd.DataFrame(data=tukeyMonth._results_table.data[1:], columns=tukeyMonth._results_table.data[0])

tukeyResultsSummary = summariseTukeyTest(tukeyResultsMonth, "ArrivalMonth")

print("Month of the year Tukey test results")
print(tukeyResultsSummary)

# perform Tukey test for ArrivalDayOfWeek
tukeyDayOfWeek = sm_stats.multicomp.pairwise_tukeyhsd(transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["LateSeenByDr"], transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["ArrivalDayOfWeek"])

tukeyResultsDayOfWeek = pd.DataFrame(data=tukeyDayOfWeek._results_table.data[1:], columns=tukeyDayOfWeek._results_table.data[0])

tukeyResultsDayOfWeekSummary = summariseTukeyTest(tukeyResultsDayOfWeek, "ArrivalDayOfWeek")

print("Day of the week Tukey test results")
print(tukeyResultsDayOfWeekSummary)

# test 