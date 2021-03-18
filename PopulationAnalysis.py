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
import seaborn as sns
import matplotlib.pyplot as plt
import statsmodels.stats.multicomp as sm_stats
import statsmodels.formula.api as sm_formula

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
        tukeySummaryDf.loc[tukeySummaryDf[factor]==group1, "StatisticallySignificantInstance"] += 1
        tukeySummaryDf.loc[tukeySummaryDf[factor]==group2, "StatisticallySignificantInstance"] += 1
        if tukeyTrue.iloc[i]["meandiff"] < 0:
            tukeySummaryDf.loc[tukeySummaryDf[factor]==group1, "Worse"] += 1
            tukeySummaryDf.loc[tukeySummaryDf[factor]==group2, "Better"] += 1
        else:
            tukeySummaryDf.loc[tukeySummaryDf[factor]==group1, "Better"] += 1
            tukeySummaryDf.loc[tukeySummaryDf[factor]==group2, "Worse"] += 1
            
    tukeySummaryDf = pd.DataFrame(tukeySummaryDf)
    
    return tukeySummaryDf

# set graph settings
sns.set(rc={'axes.facecolor':'#404040', 'figure.facecolor': '#404040'})

# read dataset and timeline
transformedDataset = pd.read_excel("output.xlsx", sheet_name="Dataset_ED_transformed")
presentationTimeline = pd.read_excel("output.xlsx", sheet_name="ED Wait Room Timeline")

# rename columns
transformedDataset.rename(columns={"Triage Priority": "TriagePriority", "Arrival Month": "ArrivalMonth", "Arrival Day Of Week": "ArrivalDayOfWeek", "TimeDiff Arrival-TreatDrNr (mins)": "TimeDiffArrival_TreatDrNr_mins", " Age  (yrs)": "Age (years)"}, inplace=True)

# analyse prevalence of patients treated later than their expected ordering
TreatedLater_Triage_agg = transformedDataset.groupby(by=["TriagePriority", "TreatedLaterThanOrdering"])["MRN"].count().reset_index()
print(TreatedLater_Triage_agg)
fig, ax = plt.subplots(figsize=(15,12))
ax = sns.barplot(x="TriagePriority", y="MRN", data=TreatedLater_Triage_agg.loc[TreatedLater_Triage_agg["TreatedLaterThanOrdering"]==1], color="#ffe600", label="Treated later than expected priority")
ax = sns.barplot(x="TriagePriority", y="MRN", data=TreatedLater_Triage_agg.loc[TreatedLater_Triage_agg["TreatedLaterThanOrdering"]==0], color="#cccccc", bottom=list(TreatedLater_Triage_agg.loc[TreatedLater_Triage_agg["TreatedLaterThanOrdering"]==1]["MRN"]), label="Not treated later than expected priority")
ax.set_xlabel("Patient Triage Priority")
ax.set_ylabel("Count")
ax.xaxis.label.set_color('w')
ax.yaxis.label.set_color('w')
ax.xaxis.label.set_size(20)
ax.yaxis.label.set_size(20)
ax.tick_params(axis='x', colors='w')
ax.tick_params(axis="both", which="major", labelsize=15)
ax.tick_params(axis='y', colors='w')
plt.setp(ax.legend().get_texts(), color='w', fontsize=15)
ax.grid(False)
plt.show()
fig.savefig("TreatedLaterThanOrdering_bar.png", dpi=fig.dpi, bbox_inches='tight')

# Triage priorities 3 and 4 are most likely to be treated later than their ordering. Find out who they tend to lose out on priority to
# analyse triage priority 3 first
triage_3 = transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["TriagePriority"]==3)].reset_index(drop=True)
for i in range(len(triage_3)):
    MRN = triage_3.iloc[i]["MRN"]
    PresentationVisitNumber = triage_3.iloc[i]["Presentation Visit Number"]
    ExpectedSeen = triage_3.iloc[i]["Expected Dr Seen"]
    ActualSeen = triage_3.iloc[i]["Dr Seen Date"]
    datetimes = list(presentationTimeline.loc[(presentationTimeline["MRN"]==MRN) & (presentationTimeline["Presentation Visit Number"]==PresentationVisitNumber)]["Datetime"].unique())
    bumpedBy = presentationTimeline.loc[(presentationTimeline["MRN"]!=MRN) & (presentationTimeline["Presentation Visit Number"]!=PresentationVisitNumber) & (presentationTimeline["Datetime"].isin(datetimes)) & (presentationTimeline["Expected Dr Seen"]>ExpectedSeen) & (presentationTimeline["Actual Dr Seen"]<ActualSeen)].drop_duplicates(subset=["MRN", "Presentation Visit Number"], keep="first")[["Triage Priority", "MRN"]]
    bumpedByTriage = bumpedBy.groupby(by="Triage Priority")["MRN"].count().reset_index()
    for triage in range(1, 6):
        try:
            transformedDataset.loc[(transformedDataset["MRN"]==MRN) & (transformedDataset["Presentation Visit Number"]==PresentationVisitNumber), "BumpedByTriage{}".format(triage)] = int(bumpedByTriage.loc[bumpedByTriage["Triage Priority"]==triage]["MRN"])
        except TypeError:
            pass
        
# analyse triage priority 4
triage_4 = transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["TriagePriority"]==4)].reset_index(drop=True)
for i in range(len(triage_4)):
    MRN = triage_4.iloc[i]["MRN"]
    PresentationVisitNumber = triage_4.iloc[i]["Presentation Visit Number"]
    ExpectedSeen = triage_4.iloc[i]["Expected Dr Seen"]
    ActualSeen = triage_4.iloc[i]["Dr Seen Date"]
    datetimes = list(presentationTimeline.loc[(presentationTimeline["MRN"]==MRN) & (presentationTimeline["Presentation Visit Number"]==PresentationVisitNumber)]["Datetime"].unique())
    bumpedBy = presentationTimeline.loc[(presentationTimeline["MRN"]!=MRN) & (presentationTimeline["Presentation Visit Number"]!=PresentationVisitNumber) & (presentationTimeline["Datetime"].isin(datetimes)) & (presentationTimeline["Expected Dr Seen"]>ExpectedSeen) & (presentationTimeline["Actual Dr Seen"]<ActualSeen)].drop_duplicates(subset=["MRN", "Presentation Visit Number"], keep="first")[["Triage Priority", "MRN"]]
    bumpedByTriage = bumpedBy.groupby(by="Triage Priority")["MRN"].count().reset_index()
    for triage in range(1, 6):
        try:
            transformedDataset.loc[(transformedDataset["MRN"]==MRN) & (transformedDataset["Presentation Visit Number"]==PresentationVisitNumber), "BumpedByTriage{}".format(triage)] = int(bumpedByTriage.loc[bumpedByTriage["Triage Priority"]==triage]["MRN"])
        except TypeError:
            pass

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
    populationRank = transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["LateSeenByDr", "TreatedLaterThanOrdering", "TriagePriority"]]
    populationRank['Rank'] = populationRank["LateSeenByDr"].rank(method='average')
    sumRank_0 = populationRank.loc[populationRank["TreatedLaterThanOrdering"]==0]["Rank"].sum()
    meanRank_0 = sumRank_0/(len(populationRank.loc[populationRank["TreatedLaterThanOrdering"]==0]))
    sumRank_1 = populationRank.loc[populationRank["TreatedLaterThanOrdering"]==1]["Rank"].sum()
    meanRank_1 = sumRank_1/(len(populationRank.loc[populationRank["TreatedLaterThanOrdering"]==1]))
    
    median_0 = populationRank.loc[populationRank["TreatedLaterThanOrdering"]==0]["LateSeenByDr"].median()
    median_1 = populationRank.loc[populationRank["TreatedLaterThanOrdering"]==1]["LateSeenByDr"].median()
    
    SumMeanRankTable = pd.DataFrame({"TreatedLaterThanOrdering": [0, 1], "Mean rank": [meanRank_0, meanRank_1], "Median": [median_0, median_1]})
    
    print("Mean rank table")
    print(SumMeanRankTable)

# graph density for TreatedLaterThanOrdering and LateSeenByDr
fig, ax = plt.subplots(figsize=(15,12))
ax.set_title = "Density Plot Of Length Of Time Patients Receive Medical Treatment Later Than Appropriate Triage Timeframe For Populations TreatedLaterThanOrder = {0, 1}"
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==0)]["LateSeenByDr"], label="Not treated later than expected order", ax=ax, shade=True, color='#cccccc')
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==1)]["LateSeenByDr"], label="Treated later than expected order", ax=ax, shade=True, color='#ffe600')
ax.set_xlabel("Late time (mins)")
ax.set_ylabel("Probability Density")
ax.xaxis.label.set_color('w')
ax.yaxis.label.set_color('w')
ax.xaxis.label.set_size(20)
ax.yaxis.label.set_size(20)
ax.tick_params(axis='x', colors='w')
ax.tick_params(axis="both", which="major", labelsize=15)
ax.tick_params(axis='y', colors='w')
plt.axvline(x=median_1, color='#ffe600')
plt.axvline(x=median_0, color='#cccccc')
plt.text(median_1 + 10, 0.0175, str(int(median_1)), color='w', fontsize=15)
plt.text(median_0 + 10, 0.0175, str(int(median_0)), color='w', fontsize=15)
plt.setp(ax.legend().get_texts(), color='w', fontsize=15)
ax.grid(False)
plt.show()
fig.savefig("TreatedLaterThanOrdering.png", dpi=fig.dpi, bbox_inches='tight')

# multi-factor linear regression
# calculate accepatable range
mean = transformedDataset["LateSeenByDr"].mean()
threeStd = transformedDataset["LateSeenByDr"].std() * 3
lowerBound = mean - threeStd
upperBound = mean + threeStd

populationRank = transformedDataset.loc[~transformedDataset["LateSeenByDr"].isna()][["LateSeenByDr", "TreatedLaterThanOrdering", "TriagePriority"]]
mask_0 = populationRank["TreatedLaterThanOrdering"]==0
mask_1 = populationRank["TreatedLaterThanOrdering"]==1
populationRank.loc[mask_0, "TreatedLaterThanOrdering_0"] = 1
populationRank.loc[mask_1, "TreatedLaterThanOrdering_1"] = 1
populationRank.loc[mask_1, "TreatedLaterThanOrdering_0"] = 0
populationRank.loc[mask_0, "TreatedLaterThanOrdering_1"] = 0

## using scikit-learn
reg = linear_model.Lasso()
reg.fit(populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["LateSeenByDr"] >= lowerBound) & (populationRank["LateSeenByDr"] <= upperBound)][["TreatedLaterThanOrdering_0", "TreatedLaterThanOrdering_1"]], populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["LateSeenByDr"] >= lowerBound) & (populationRank["LateSeenByDr"] <= upperBound)]["LateSeenByDr"])

# calculate r2 of model
r2 = reg.score(populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["LateSeenByDr"] >= lowerBound) & (populationRank["LateSeenByDr"] <= upperBound)][["TreatedLaterThanOrdering_0", "TreatedLaterThanOrdering_1"]], populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["LateSeenByDr"] >= lowerBound) & (populationRank["LateSeenByDr"] <= upperBound)]["LateSeenByDr"])

print("R2: {}".format(r2))
print("Coef: {}".format(reg.coef_))

# analyse TreatedLaterThanOrdering disaggregated by current patient's triage priority
formula = "LateSeenByDr ~ C(TreatedLaterThanOrdering)*C(TriagePriority)"
lm = sm_formula.ols(formula, transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]).fit()
print(lm.summary())

transformedDataset["TreatedLaterThanOrdering_TriagePriority"] = transformedDataset["TreatedLaterThanOrdering"].astype(str) + "/" + transformedDataset["TriagePriority"].astype(str)

tukeyTreatedLateTriage = sm_stats.pairwise_tukeyhsd(transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["LateSeenByDr"], transformedDataset.loc[~(transformedDataset["LateSeenByDr"].isna()) & (transformedDataset["LateSeenByDr"] >= lowerBound) & (transformedDataset["LateSeenByDr"] <= upperBound)]["TreatedLaterThanOrdering_TriagePriority"])

tukeyResultsTreatedLateTriage = pd.DataFrame(data=tukeyTreatedLateTriage._results_table.data[1:], columns=tukeyTreatedLateTriage._results_table.data[0])

tukeyResultsSummary = summariseTukeyTest(tukeyResultsTreatedLateTriage, "TreatedLater_TriagePriority")

print("Treated late - triage Tukey test results")
print(tukeyResultsSummary)

# analyse effect of being treated late against triage priority 3 population
treatedLate_0_triage_3 = populationRank.loc[(populationRank["TreatedLaterThanOrdering"]==0) & (populationRank["TriagePriority"]==3)]
treatedLate_1_triage_3 = populationRank.loc[(populationRank["TreatedLaterThanOrdering"]==1) & (populationRank["TriagePriority"]==3)]

mannWhitneyU = stats.mannwhitneyu(treatedLate_0_triage_3, treatedLate_1_triage_3)
if mannWhitneyU[1] < 0.05:
    print("--- P-value: {}\nStatistically significant!".format(mannWhitneyU[1]))

median_0_3 = treatedLate_0_triage_3["LateSeenByDr"].median()
median_1_3 = treatedLate_1_triage_3["LateSeenByDr"].median()

# graph density for TreatedLaterThanOrdering and LateSeenByDr
fig, ax = plt.subplots(figsize=(15,12))
ax.set_title = "Density Plot Of Length Of Time Patients Receive Medical Treatment Later Than Appropriate Triage Timeframe For Populations TreatedLaterThanOrder = {0, 1}"
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==0) & (populationRank["TriagePriority"]==3)]["LateSeenByDr"], label="Not treated later than expected order", ax=ax, shade=True, color='#cccccc')
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==1) & (populationRank["TriagePriority"]==3)]["LateSeenByDr"], label="Treated later than expected order", ax=ax, shade=True, color='#fc7303')
ax.set_xlabel("Late time (mins)")
ax.set_ylabel("Probability Density")
ax.xaxis.label.set_color('w')
ax.yaxis.label.set_color('w')
ax.xaxis.label.set_size(20)
ax.yaxis.label.set_size(20)
ax.tick_params(axis='x', colors='w')
ax.tick_params(axis="both", which="major", labelsize=15)
ax.tick_params(axis='y', colors='w')
plt.axvline(x=median_1_3, color='#fc7303')
plt.axvline(x=median_0_3, color='#cccccc')
plt.text(median_1_3 + 10, 0.02, str(int(median_1_3)), color='w', fontsize=15)
plt.text(median_0_3 + 10, 0.02, str(int(median_0_3)), color='w', fontsize=15)
plt.setp(ax.legend().get_texts(), color='w', fontsize=15)
ax.grid(False)
plt.show()
fig.savefig("TreatedLaterThanOrdering_triage3.png", dpi=fig.dpi, bbox_inches='tight')

# analyse effect of being treated late against triage priority 4 population
treatedLate_0_triage_4 = populationRank.loc[(populationRank["TreatedLaterThanOrdering"]==0) & (populationRank["TriagePriority"]==4)]
treatedLate_1_triage_4 = populationRank.loc[(populationRank["TreatedLaterThanOrdering"]==1) & (populationRank["TriagePriority"]==4)]

mannWhitneyU = stats.mannwhitneyu(treatedLate_0_triage_4, treatedLate_1_triage_4)
if mannWhitneyU[1] < 0.05:
    print("--- P-value: {}\nStatistically significant!".format(mannWhitneyU[1]))

median_0_4 = treatedLate_0_triage_4["LateSeenByDr"].median()
median_1_4 = treatedLate_1_triage_4["LateSeenByDr"].median()

# graph density for TreatedLaterThanOrdering and LateSeenByDr
fig, ax = plt.subplots(figsize=(15,12))
ax.set_title = "Density Plot Of Length Of Time Patients Receive Medical Treatment Later Than Appropriate Triage Timeframe For Populations TreatedLaterThanOrder = {0, 1}"
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==0) & (populationRank["TriagePriority"]==4)]["LateSeenByDr"], label="Not treated later than expected order", ax=ax, shade=True, color='#cccccc')
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==1) & (populationRank["TriagePriority"]==4)]["LateSeenByDr"], label="Treated later than expected order", ax=ax, shade=True, color='#fcc603')
ax.set_xlabel("Late time (mins)")
ax.set_ylabel("Probability Density")
ax.xaxis.label.set_color('w')
ax.yaxis.label.set_color('w')
ax.xaxis.label.set_size(20)
ax.yaxis.label.set_size(20)
ax.tick_params(axis='x', colors='w')
ax.tick_params(axis="both", which="major", labelsize=15)
ax.tick_params(axis='y', colors='w')
plt.axvline(x=median_1_4, color='#fcc603')
plt.axvline(x=median_0_4, color='#cccccc')
plt.text(median_1_4 + 10, 0.014, str(int(median_1_4)), color='w', fontsize=15)
plt.text(median_0_4 + 10, 0.014, str(int(median_0_4)), color='w', fontsize=15)
plt.setp(ax.legend().get_texts(), color='w', fontsize=15)
ax.grid(False)
plt.show()
fig.savefig("TreatedLaterThanOrdering_triage4.png", dpi=fig.dpi, bbox_inches='tight')

# analyse effect of being treated late against triage priority 5 population
treatedLate_0_triage_5 = populationRank.loc[(populationRank["TreatedLaterThanOrdering"]==0) & (populationRank["TriagePriority"]==5)]
treatedLate_1_triage_5 = populationRank.loc[(populationRank["TreatedLaterThanOrdering"]==1) & (populationRank["TriagePriority"]==5)]

mannWhitneyU = stats.mannwhitneyu(treatedLate_0_triage_5, treatedLate_1_triage_5)
if mannWhitneyU[1] < 0.05:
    print("--- P-value: {}\nStatistically significant!".format(mannWhitneyU[1]))

median_0_5 = treatedLate_0_triage_5["LateSeenByDr"].median()
median_1_5 = treatedLate_1_triage_5["LateSeenByDr"].median()

# graph density for TreatedLaterThanOrdering and LateSeenByDr
fig, ax = plt.subplots(figsize=(15,12))
ax.set_title = "Density Plot Of Length Of Time Patients Receive Medical Treatment Later Than Appropriate Triage Timeframe For Populations TreatedLaterThanOrder = {0, 1}"
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==0) & (populationRank["TriagePriority"]==5)]["LateSeenByDr"], label="Not treated later than expected order", ax=ax, shade=True, color='#cccccc')
ax = sns.kdeplot(data=populationRank.loc[(~populationRank["LateSeenByDr"].isna()) & (populationRank["TreatedLaterThanOrdering"]==1) & (populationRank["TriagePriority"]==5)]["LateSeenByDr"], label="Treated later than expected order", ax=ax, shade=True, color='#fcf803')
ax.set_xlabel("Late time (mins)")
ax.set_ylabel("Probability Density")
ax.xaxis.label.set_color('w')
ax.yaxis.label.set_color('w')
ax.xaxis.label.set_size(20)
ax.yaxis.label.set_size(20)
ax.tick_params(axis='x', colors='w')
ax.tick_params(axis="both", which="major", labelsize=15)
ax.tick_params(axis='y', colors='w')
plt.axvline(x=median_1_5, color='#fcf803')
plt.axvline(x=median_0_5, color='#cccccc')
plt.text(median_1_5 + 10, 0.013, str(int(median_1_5)), color='w', fontsize=15)
plt.text(median_0_5 + 10, 0.013, str(int(median_0_5)), color='w', fontsize=15)
plt.setp(ax.legend().get_texts(), color='w', fontsize=15)
ax.grid(False)
plt.show()
fig.savefig("TreatedLaterThanOrdering_triage5.png", dpi=fig.dpi, bbox_inches='tight')

# output results
with pd.ExcelWriter("TreatedLaterThanOrdering_TestResults.xlsx") as excelwriter:
    transformedDataset.to_excel(excelwriter, sheet_name="Transformed dataset", index=False)
    presentationTimeline.to_excel(excelwriter, sheet_name="ED Wait Room Timeline", index=False)
    SumMeanRankTable.to_excel(excelwriter, sheet_name="MeanRank", index=False)
    tukeyResultsTreatedLateTriage.to_excel(excelwriter, sheet_name="TukeyResults", index=False)
    tukeyResultsSummary.to_excel(excelwriter, sheet_name="TukeyResultsSummary")