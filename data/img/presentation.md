https://www.youtube.com/watch?v=WrX_BZWzF74&amp=&feature=youtu.be
## Presentation Format
**Approach to the presentation:** what does hiring manager want to know about you? 
**Length**: 5-6 minutes
**How:** Using Zoom, if microphone of laptop is iffy, we recommend using a headset/
**Structure:**
1. Intro: Name, Data Science Track

 
2. Brief App and Team Introduction

Mention Teamates

The Investment Risk Ratings Project has one overarching goal: to make equities investing simpler and safer by accurately assessing what the market factors that contribute to the risk of investing in a given company are. All investors, from the retail investor to the professional hedge fund manager, are faced with the daunting task of assimilating a forbiddingly vast amount of information that is changing on a daily basis, a cognitive demand that no one can master.

By systematically breaking down the movement of a company’s stock price into its constituent factors - whether macroeconomic, technical, or fundamental - we can help diminish the overwhelming complexity of the investment process, and in turn make investing both a safer and more rational process.


2. Technical skills/languages
 - Python
     - Artificial Neural Networks
 - Data Ingestion Engine
     - OOP
     - Alpha Vantage, Intrinio, Quandl APIs, Pandas
 - Modeling 
     - LSTM-RNN using Keras with a TensorFlow Backend
     - Modified Scikit learn wrapper with bespoke grid search
 - Interpretability
     - Shapley Values provided by SHAP

 - Model training takes place of AWS

4. Demo the product (share screen) /show code (if needed), 

- Mention data ingestion engine
- Show images in slide-deck from 2nd Canvas to demonstrate modeling and interpretability output
- Move on to Custom Grid Search Paramters
- Mention further automation for training and saving model weights.

    1. Problem solving skill (approach taken, options considered to solve a problem)
    2. Collaboration skill (a story of working with others, experience working on a team, etc.)
    3. Planning skill (project management, stories, project breakdown)
    
    
Start with stories: interviewing Quants in industry. Mention current quantitative analysis SOP involving finding monotonic correlation (spearman's rho). We want to find more than just traditional correlation, but find interaction between features. 
    
This project was incredibly technical, demanding a wide-variety of skillsets. Our approach was iterative, tackling each major component one after another. Our first challenge was reliable and flexible data ingestion. This we achieved by creating a DailyTimeSeries class that incorporated Equity Prices, Macroeconomic Indicators, Technicals and Fundamentals. 

We then moved on to modeling. Our goal was to create a decently generalizable model from which we can extract feature interactions. To better tune our model paramters, we created a custom grid search by breaking down the Keras Sklearn wrapper to better fit our needs. This search then iterates through a list of equities we want to analyze saving the model weights to another directory. 

Our feature interactions are then extracted via a methodology from Game Theory called Shapley Values:

The goal of SHAP is to explain the prediction of an instance x by computing the contribution of each feature to the prediction. The SHAP explanation method computes Shapley values from coalitional game theory. The feature values of a data instance act as players in a coalition. Shapley values tell us how to fairly distribute the “payout” (= the prediction) among the features. The Shapley value is the average marginal contribution of a feature value across all possible Combinations.

The benefit of using the SHAP library is that it provides us with a global view of the interactions as well as a very localized view per timestep sample. As a result, we can return a depth of information to our stakeholder. 

The team collaborated heavily on the devlopment of each method in the data ingestion engine, as well as modeling the equity prices. Our process involved siloing for several days and returning to integrate individual methodologies. This allowed us to build off of eachother's work without influencing research paths overmuch. 