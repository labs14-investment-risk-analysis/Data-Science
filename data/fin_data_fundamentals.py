from decouple import config
from time import sleep
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


def get_fundamentals(tkr_id,
                     after_date,
                     end_date='',
                     fundamentals_toget = 'all',
                     sandbox=False):

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

    available_data = get_intrinio_fids(tkr_id=tkr_id,
                     after_date=after_date,
                     end_date=end_date,
                     sandbox=sandbox)

    qtrs = ['Q1', 'Q2', 'Q3', 'Q4']
    income_statements = []

    # Sort for income statements from quarterly reports
    # Note: sorting for income statements is also done in api call
    # but am leaving it here in case of irregularities

    for report in available_data:
        if (report.statement_code == 'income_statement') & (report.fiscal_period in qtrs):
            income_statements.append(report)

    fids_list = []
    for report in income_statements:
        fids_list.append(report.id)

    fund_dict = fundamentals_from_fids(fids_list=fids_list, sandbox=sandbox)

    # Reformat the dictionary for easy conversion to dataframe
    temp_dict = {}

    # Check which fundamentals to return. 'all' returns all available
    #funs_available = fund_dict[first_fun[0]].keys()
    #print(first_fun)
    if fundamentals_toget == 'all':
        # Format by adding ticker id to fundamental name
        # for all columns except date
        list_fun_toget = find_fundamentals(tkr_id=tkr_id,
                                           sandbox=sandbox,
                                           nocomm=True)
        for fun in list_fun_toget:
            if fun != 'date':
                temp_dict[str(tkr_id + '_' + fun)] = []
    else:
        # Same if list of fundamentals is used.
        for fun in fundamentals_toget:
            if fun != 'date':
                temp_dict[tkr_id + '_' + fun] = []
    # Add date to dictionary
    if 'date' not in temp_dict.keys():
        temp_dict['date'] = []

    # Most companies only make yearly reports for Q4, so fill in
    # first date if missing.
    # if fund_dict[list(fund_dict.keys())[0]]['date'] == None:
    #     fund_dict[list(fund_dict.keys())[0]]['date'] = increment_months(
    #         fund_dict[list(fund_dict.keys())[1]]['date'], -3)
    
    prev_date_assigned = False

    
    for fun_key in fund_dict.keys():
        if prev_date_assigned == False:
            if fund_dict[fun_key]['date'] == None:
                fund_dict[fun_key]['date'] = after_date
        # Populate dictionary, filling in date if it is missing
        # with date 3 months after previous date
        for fun in temp_dict.keys():
            # 'date' needs to be handled differently than other columns
            if fun != 'date':
                temp_dict[fun].append(fund_dict[fun_key][fun.split('_')[1]]
                                      if fun.split('_')[1]
                                      in list(fund_dict[fun_key].keys())
                                      else 0)
            elif fun == 'date':
                temp_dict[fun].append(fund_dict[fun_key][fun].strftime("%Y-%m-%d")
                                       if fund_dict[fun_key]['date'] != None
                                       else increment_months(previous_date, 3)
                                      .strftime("%Y-%m-%d"))
                previous_date = fund_dict[fun_key]['date']
                prev_date_assigned = True
    return_df = pd.DataFrame(temp_dict)
    # if nocomm == True:
    #     if (str(tkr_id + '_quarter' in return_df.columns)):
    #         return_df = return_df.drop(labels=('{}_quarter'.format(tkr_id)))
    #     if (str(tkr_id +  '_fiscal_year') in return_df.columns):
    #         return_df = return_df.drop(labels=('{}_fiscal_year'.format(tkr_id)))
    return(return_df)


def fundamentals_from_fids(fids_list, sandbox=False):

    if sandbox == False:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_KEY')

        security_api = intrinio_sdk.SecurityApi()
    elif sandbox == True:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_SANDBOX_KEY')

        security_api = intrinio_sdk.SecurityApi()

    # Initialize api's
    fapi = intrinio_sdk.FundamentalsApi()

    fund_dict = {}
    for id in fids_list:
        for attempt in range(5):
            try:
                fundamentals_ret = fapi.get_fundamental_standardized_financials(id)
            except:
                print('Connection error. Retry attempt {}'.format(attempt))
                sleep(2)
            else:
                break
        fund_get = fundamentals_ret.standardized_financials_dict
        fund_info = fundamentals_ret.fundamental_dict
        funds = {}
        funds['date'] = fund_info['filing_date']
        funds['fiscal_year'] = fund_info['fiscal_year']
        funds['quarter'] = fund_info['fiscal_period']
        for f in fund_get:
            funds[f['data_tag']['tag'].lower()] = f['value']
        fund_dict[id] = funds
    return fund_dict

def get_intrinio_fids(tkr_id,
                     after_date,
                     end_date='',
                     sandbox=False):
    if sandbox == False:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_KEY')

        security_api = intrinio_sdk.SecurityApi()
    elif sandbox == True:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_SANDBOX_KEY')

        security_api = intrinio_sdk.SecurityApi()

    # Initialize api's
    capi = intrinio_sdk.CompanyApi()

    capi_params = {
        'identifier'     : tkr_id,
        'filed_after'    : '',
        'filed_before'   : '',
        'reported_only'  : False,
    #     'fiscal_year'  : fiscal_year,
        'statement_code' : 'income_statement',
        'type'           : 'QTR',
        'start_date'     : after_date,
        'end_date'       : end_date,
        'page_size'      : 500,
        'next_page'      : ''
    }


    # Set up dictionary to populate with financial report availibility information
    for attempt in range(5):
        try:
            fundamentals = capi.get_company_fundamentals(**capi_params)
        except:
            print("There was a server error. Retrying, attempt {}.".format(attempt))
            sleep(5)
        else:
            break
    # n_results = len(fundamentals.fundamentals)
    # for i in range(n_results):
    #     if fundamentals.fundamentals[i].filing_date != None:
    #         fundamentals.fundamentals[i].filing_date = fundamentals.fundamentals[i].filing_date.strftime('%Y-%m-%d')

    return(fundamentals.fundamentals)

        
def find_fundamentals(tkr_id, sandbox = False, nocomm=False):
    
    """
    Returns a list of available fundamental financial indicators for the
    specified company.
    
    -- tkr_id: stock ticker name. 'AAPL' for Apple inc, 'XOM' for Exxon Mobile Corp. etc.
            (if using a developer sandbox key, only DOW 30 will be available)
    
    -- sandbox: Use this to turn sandbox mode on and off if you have a developers 
        sandbox api key. Limited to DOW 30, but much less strict limits on api calls.
        
    *In .env file name main key INTRINIO_KEY and developer sandbox key INTRINIO_SANDBOX_KEY
    """

    # Sandbox check and get env key
    if sandbox == False:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_KEY')

        security_api = intrinio_sdk.SecurityApi()
    elif sandbox == True:
        intrinio_sdk.ApiClient().configuration.api_key['api_key'] = config('INTRINIO_SANDBOX_KEY')

        security_api = intrinio_sdk.SecurityApi()
    
    # Initialize api's
    capi = intrinio_sdk.CompanyApi()
    fapi = intrinio_sdk.FundamentalsApi()
    
    # Set parameters to get most recent financial report
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
    
    # Get most recent financials report
    fundamentals = capi.get_company_fundamentals(**fund_params)
    id_to_check = fundamentals.fundamentals[0].id
    fun_check = fapi.get_fundamental_standardized_financials(id_to_check)
    
    available_fun = []
    
    common = ['date', 'fiscal_year', 'quarter']
    
    # Make list of available fundamentals and add above
    for fun in fun_check.standardized_financials:
        available_fun.append(fun.data_tag.tag)
    if nocomm == False:
        for fun in common:
            available_fun.append(fun)
    else:
        available_fun.append('date')
    return(available_fun)
    

    
