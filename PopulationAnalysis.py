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

# read dataset and timeline
transformedDataset = pd.read_excel("output.xlsx", sheet_name="Dataset_ED_transformed")
presentationTimeline = pd.read_excel("output.xlsx", sheet_name="Presentation Timeline")

# test assumption that LateSeenByDr is a normal distr
normTest = stats.shapiro(transformedDataset["LateSeenByDr"])

# t-test for TreatedLaterThanOrdering
res = stats.ttest_ind(transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==0) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"], transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==1) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"], equal_var=False)

# graph density for TreatedLaterThanOrdering and LateSeenByDr
ax = transformedDataset[["TreatedLaterThanOrdering", "LateSeenByDr"]].pivot(columns="TreatedLaterThanOrdering", values="LateSeenByDr").plot.density(alpha=0.5, figsize=(15, 12))

# multi-variate linear regression
# calculate accepatable range
mean = transformedDataset["LateSeenByDr"].mean()
threeStd = transformedDataset["LateSeenByDr"].std() * 3
lowerBound = mean - threeStd
upperBound = mean + threeStd

# using scikit-learn
reg = linear_model.LinearRegression()
reg.fit(transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["Triage 1 count", "Triage 2 count", "Triage 3 count", "Triage 4 count", "Triage 5 count"]], transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()]["LateSeenByDr"])

# calculate r2 of model
r2 = reg.score(transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["TotalPatientsInEDAtArrival", "Triage 1 count", "Triage 2 count", "Triage 3 count", "Triage 4 count", "Triage 5 count"]], transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()]["LateSeenByDr"])

# using statsmodel
est = sm.OLS(transformedDataset.loc[(~transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["LateSeenByDr"], transformedDataset.loc[(~transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)][["Triage 1 count", "Triage 2 count", "Triage 3 count", "Triage 4 count", "Triage 5 count"]])

est = est.fit()

print(est.summary())