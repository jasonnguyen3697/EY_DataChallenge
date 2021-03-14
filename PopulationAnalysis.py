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

# read dataset and timeline
transformedDataset = pd.read_excel("output.xlsx", sheet_name="Dataset_ED_transformed")
presentationTimeline = pd.read_excel("output.xlsx", sheet_name="Presentation Timeline")

# calculate population treated after their expected ordering
dateTimeTreatedLaterThanOrdering = list(presentationTimeline.loc[presentationTimeline["Actual Ranking"] > presentationTimeline["Expected Ranking"]]["Datetime"].unique())
treatedLaterThanOrdering = presentationTimeline.loc[presentationTimeline["Actual Ranking"] > presentationTimeline["Expected Ranking"]][["MRN", "Presentation Visit Number"]].drop_duplicates(subset=["MRN", "Presentation Visit Number"], keep="first")

# add flag to transformed dataset
transformedDataset = transformedDataset.merge(treatedLaterThanOrdering, how="left", on=["MRN", "Presentation Visit Number"], indicator=True)
mask = transformedDataset["_merge"] == "both"
transformedDataset.loc[mask, "TreatedLaterThanOrdering"] = 1
transformedDataset.loc[~mask, "TreatedLaterThanOrdering"] = 0
transformedDataset.drop(labels=["_merge"], axis="columns", inplace=True)

# test assumption that LateSeenByDr is a normal distr
normTest = stats.shapiro(transformedDataset["LateSeenByDr"])

# t-test for TreatedLaterThanOrdering
res = ttest_ind(transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==0) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"], transformedDataset.loc[(transformedDataset["TreatedLaterThanOrdering"]==1) & ~(transformedDataset["LateSeenByDr"].isna())]["LateSeenByDr"], equal_var=False)

# graph density for TreatedLaterThanOrdering and LateSeenByDr
ax = transformedDataset[["TreatedLaterThanOrdering", "LateSeenByDr"]].pivot(columns="TreatedLaterThanOrdering", values="LateSeenByDr").plot.density(alpha=0.5, figsize=(15, 12))