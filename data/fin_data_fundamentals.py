from decouple import config
import intrinio_sdk
from intrinio_sdk.rest import ApiException
import numpy as np 
import pandas as pd
import re
import string
import datetime
import calendar

def increment_months(orig_date, inc):
    
    """
    The increment_months() function advances or reduces month in a datetime
    object.
    
    -- orig_date: datetime object to be changed. 
    
    -- inc: number of months to increment. Accepts signed integer 
    to increment or decrement.
    """
    
    new_year = orig_date.year
    new_month = orig_date.month + inc
    # note: in datetime.date, months go from 1 to 12
    # conditional advances year if necessary 
    if new_month > 12:
        new_year += 1
        new_month -= 12
    elif new_month < 1:
        new_year -= 1
        new_month += 12

    last_day_of_month = calendar.monthrange(new_year, new_month)[1]
    new_day = min(orig_date.day, last_day_of_month)

    return orig_date.replace(year=new_year, month=new_month, day=new_day)


def get_fundamentals(tkr_id, after_date, end_date='', fundamentals_toget = 'all', sandbox=False, return_df=False, nocomm=False):

    """
    Get fundamentals indicators from the intrinio api. Returns intrinio's standardized
    fundamentals data from quartarly financial reports. Pass the ticker id, dates,
    and a list of fundamentals.
    
    -- tkr_id: stock ticker name. 'AAPL' for Apple inc, 'XOM' for Exxon Mobile Corp. etc.
            (if using a developer sandbox key, only DOW 30 will be available)
    
    -- after_date: Get fundamentals data from financial reports published after this date.
            ***Pass dates as strings in '%Y-%m-%d' format
    
    -- end_date: Default or empty string for present date. 
            ***Pass dates as strings in '%Y-%m-%d' format
    
    -- fundamentals_toget: Default 'all' or pass list of fundamentals to get. Get
        indicator names with find_fundamentals('<tickerId>') in fin_data package.
        (from fin_data import find_fundamentals)
    
    -- sandbox: Use this to turn sandbox mode on and off if you have a developers 
        sandbox api key. Limited to DOW 30, but much less strict limits on api calls.
    
    -- return_df: Return results as pandas DataFrame or as dict. Dict may be more useful
        for direct integration into other code. Returned DataFrame is formatted for use
        in the fin_data tool to integrate fundamentals data with time series indicators.

    *In .env file name main key INTRINIO_KEY and developer sandbox key INTRINIO_SANDBOX_KEY
    """


    if sandbox == False:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_KEY')

        security_api = intrinio_sdk.SecurityApi()
    elif sandbox == True:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_SANDBOX_KEY')

        security_api = intrinio_sdk.SecurityApi()

    
    capi = intrinio_sdk.CompanyApi()
    fapi = intrinio_sdk.FundamentalsApi()

    fund_params = {
        'identifier'     : tkr_id,
        'filed_after'    : '',
        'filed_before'   : '',
        'reported_only'  : False,
    #     'fiscal_year'  : fiscal_year,
        'statement_code' : 'income_statement',
        'type'           : '',
        'start_date'     : after_date,
        'end_date'       : '',
        'page_size'      : 500,
        'next_page'      : ''
    }
    
    fundamentals = capi.get_company_fundamentals(**fund_params)
    id_dict = {
        "start_date"     : [],
        "end_date"       : [],
        "fiscal_year"    : [],
        "fiscal_period"  : [],
        "id"             : [],
        "statement_code" : [],
    }

    for i in np.arange(len(fundamentals.fundamentals)):
        id_dict['start_date'].append(fundamentals.fundamentals[i].start_date)
        id_dict['end_date'].append(fundamentals.fundamentals[i].end_date) 
        id_dict['fiscal_year'].append(fundamentals.fundamentals[i].fiscal_year)
        id_dict['fiscal_period'].append(fundamentals.fundamentals[i].fiscal_period)
        id_dict['id'].append(fundamentals.fundamentals[i].id)
        id_dict['statement_code'].append(fundamentals.fundamentals[i].statement_code)

    id_df = pd.DataFrame.from_dict(id_dict)


    qtrs = ['Q1', 'Q2', 'Q3', 'Q4']
    income_statements = (id_df.loc[(id_df['statement_code'] == 'income_statement') &
                                   (id_df['fiscal_period'].isin(qtrs)==True)]
                         .sort_values(by='start_date'))

    fund_dict = {}
    for row in income_statements.iterrows():
        fundamentals_ret = fapi.get_fundamental_standardized_financials(row[1]['id'])
        fund_get = fundamentals_ret.standardized_financials_dict
        fund_info = fundamentals_ret.fundamental_dict
        funds = {}
        funds['date'] = fund_info['filing_date']
        funds['fiscal_year'] = fund_info['fiscal_year']
        funds['quarter'] = fund_info['fiscal_period']
        for f in fund_get:
            funds[f['data_tag']['tag'].lower()] = f['value']
        fund_dict[row[1]['id']] = funds

    if return_df == False:
        return(fund_dict)
    elif return_df == True:
        temp_dict = {}

        if fundamentals_toget == 'all':

            for fun in fund_dict[list(fund_dict.keys())[0]].keys():
                if fun != 'date':
                    temp_dict[str(tkr_id + '_' + fun)] = []
        else:
            for fun in fundamentals_toget:
                if fun != 'date':
                    temp_dict[tkr_id + '_' + fun] = []
        temp_dict['date'] = []

        if fund_dict[list(fund_dict.keys())[0]]['date'] == None:
            fund_dict[list(fund_dict.keys())[0]]['date'] = increment_months(fund_dict[list(fund_dict.keys())[1]]['date'], -3)

        for fun_key in fund_dict.keys():


            for fun in temp_dict.keys():
                if fun != 'date':
                    temp_dict[fun].append(fund_dict[fun_key][fun.split('_')[1]]
                                           if fun.split('_')[1] in list(fund_dict[fun_key].keys()) 
                                           else 0)
                elif fun == 'date':
                    temp_dict[fun].append(fund_dict[fun_key][fun].strftime("%Y-%m-%d")
                                           if fund_dict[fun_key]['date'] != None
                                           else increment_months(previous_date, 3).strftime("%Y-%m-%d"))
                    previous_date = fund_dict[fun_key]['date']
        return_df = pd.DataFrame(temp_dict)
        if nocomm == True:
            return_df = return_df.drop(labels=['fiscal_year', 'quarter'])
        return(return_df)
        
        
        
def find_fundamentals(tkr_id, sandbox = False):
    
    """
    Returns a list of available fundamental financial indicators for the
    specified company.
    
    -- tkr_id: stock ticker name. 'AAPL' for Apple inc, 'XOM' for Exxon Mobile Corp. etc.
            (if using a developer sandbox key, only DOW 30 will be available)
    
    -- sandbox: Use this to turn sandbox mode on and off if you have a developers 
        sandbox api key. Limited to DOW 30, but much less strict limits on api calls.
        
    *In .env file name main key INTRINIO_KEY and developer sandbox key INTRINIO_SANDBOX_KEY
    """


    if sandbox == False:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_KEY')

        security_api = intrinio_sdk.SecurityApi()
    elif sandbox == True:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_SANDBOX_KEY')

        security_api = intrinio_sdk.SecurityApi()
    
    capi = intrinio_sdk.CompanyApi()
    fapi = intrinio_sdk.FundamentalsApi()
    
    fund_params = {
        'identifier'     :tkr_id,
        'filed_after'    :'2018-06-01',
        'filed_before'   :'2018-11-01',
        'reported_only'  : False,
    #     'fiscal_year'  :fiscal_year,
        'statement_code' :'income_statement',
        'type'           :'',
        'start_date'     :'',
        'end_date'       :'',
        'page_size'      :1,
        'next_page'      :''
    }
    
    fundamentals = capi.get_company_fundamentals(**fund_params)
    id_to_check = fundamentals.fundamentals[0].id
    fun_check = fapi.get_fundamental_standardized_financials(id_to_check)
    
    available_fun = []
    
    common = ['date', 'fiscal_year', 'quarter']
    
    for fun in fun_check.standardized_financials:
        available_fun.append(fun.data_tag.tag)
    available_fun.append(common)
    return(available_fun)
    

    