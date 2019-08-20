from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.techindicators import TechIndicators
from alpha_vantage.timeseries import TimeSeries
from decouple import config
import pandas as pd
import numpy as np
import quandl
import warnings

#pylint: disable=invalid-sequence-index
#pylint: disable=no-member
#pylint: disable=unbalanced-tuple-unpacking

#TODO Warnings
#TODO Other Macro from Hira
#TODO Fundamentals from Joe

class DailyTimeSeries:
    """
    Class based data wrangling function. Uses the APIs to
    import the data, then wrangles it together.

    -----------------------------
    Attributes
    -----------------------------

    symbol : str
        string ticker used to identify the security. eg['AAPL', 'SPX'... etc.]

    interval : str
        time interval between two conscutive values,supported values
        are: ['1min', '5min', '15min', '30min', '60min', 'daily',
        'weekly', 'monthly'] (default 'daily')

    outputsize : str
        The size of the call, supported values are
        'compact' and 'full; the first returns the last 100 points in the
        data series, and 'full' returns the full-length intraday times
        series, commonly above 1MB (default 'compact')

    alpha_vantage_key : default
        api key for Alpha Vantage

    intrinio_key : default
        api key for intrinio
    
    quandl_key : default
        api key for Quandl

    -----------------------------
    Methods
    -----------------------------

    initiate :
        Produces a dataframe from the selected security's price history. No
        parameteres are needed to initialize the dataframe. Necessary first
        step for future data wrangling.

    add_securities :
        Adds price history from a list of securities and merges that data with
        the existing dataframe. Only accepts a list of securities.

    add_technicals :
        Adds technical indicators from a list of securities and merges that data
        with the existing dataframe. Only accepts a list of technical indicators.

    add_forex :
        Adds FOREX rates to the dataset. Currently only incorporates a couple of years
        ############ Recommend against using until improved ##########################

    add_macros :
        Adds all the macro indicators including US treasury Bond interest rates,
        National Housing Price Index, Trade-Weighted Dollar Price Index, Investors
        Confidence Index, to the dataset. Some Indices do not have values recorded
        for recent months and merging with other dataframes might limit the number of
        datapoints. 
    """


    def __init__(self,
                 symbol,
                 interval='daily',
                 outputsize='full',
                 alpha_vantage_key=config('ALPHA_VANTAGE'),
                 intrinio_key=config('INTRINIO_KEY'),
                 quandl_key=config('QUANDL_KEY')):

        self.symbol = symbol
        self.interval = interval
        self.outputsize = outputsize
        self.alpha_vantage_key = alpha_vantage_key
        self.intrinio_key = intrinio_key
        self.quandl_key = quandl_key

    def initiate(self):
        """
        Produces a dataframe from the selected security's price history. No
        parameteres are needed to initialize the dataframe. Necessary first
        step for future data wrangling.

        Parameters
        ----------
        None
        """
        # API Object
        ts = TimeSeries(key=self.alpha_vantage_key,
                        output_format='pandas')
        # API Call
        data, meta_data = ts.get_daily(symbol=self.symbol,
                                       outputsize=self.outputsize)

        # Print Statement
        print('###################################################################','\n',
        'Ticker: ' , meta_data['2. Symbol'], '\n',
        'Last Refreshed: ', meta_data['3. Last Refreshed'], '\n',
        'Data Retrieved: ', meta_data['1. Information'],'\n',
        '###################################################################')

        # Produce better column names
        data = data.rename(columns={
                '1. open'  : self.symbol+' open',
                '2. high'  : self.symbol+' high',
                '3. low'   : self.symbol+' low',
                '4. close' : self.symbol+' close',
                '5. volume': self.symbol+' volume'
        }
    )
        return data

    def add_securities(self, symbols, primary_df):
        """
        Adds price history from a list of securities and merges that data with
        the existing dataframe. Only accepts a list of securities.

        Parameters
        ----------
        symbols : list
            list of security symbols to add to the dataframe.
        primary_df : pandas dataframe
            pandas dataframe to be appended.

        """
        # API Object
        ts = TimeSeries(key=self.alpha_vantage_key,
                        output_format='pandas')

        # Loop through the list of securities
        i_count = 0
        for symbol in symbols:

            data, meta_data = ts.get_daily(symbol=symbol,
                                           outputsize=self.outputsize)

            # Print Statement
            print('###################################################################','\n',
            'Ticker: ' , meta_data['2. Symbol'], '\n',
            'Last Refreshed: ', meta_data['3. Last Refreshed'], '\n',
            'Data Retrieved: ', meta_data['1. Information'],'\n',
            '###################################################################')

            # Give the columns a better name
            data = data.rename(columns={
                    '1. open'  : symbol+' open',
                    '2. high'  : symbol+' high',
                    '3. low'   : symbol+' low',
                    '4. close' : symbol+' close',
                    '5. volume': symbol+' volume'
            }
        )
            # Merge Dataframes
            if i_count == 0:
                final_df = primary_df.merge(data,
                                            how='inner',
                                            on='date')
            else:
                final_df = final_df.merge(data,
                                          how='inner',
                                          on='date')
            i_count+=1
        return final_df

    def add_technicals(self, tech_symbols, primary_df, supp_symbol=None):
        """
        Adds technical indicators from a list of securities and merges that data
        with the existing dataframe. Only accepts a list of technical indicators.

        Parameters
        ----------
        tech_symbols : list
            list of technical indicator abbreviations to add to the dataframe.
            please refer to the readme.md for more information about valid
            technical indicator abbreviations.
        primary_df : pandas dataframe
            pandas dataframe to be appended.
        supp_symbol : str
            (optional) security symbol for a different symbol than the one
            defined as an object attribute. Used for comparing technical
            indicators from other securities.
        """
        # Check for supplimental symbol
        if supp_symbol ==  None:
            symbol = self.symbol
        else:
            symbol = supp_symbol

        # API Object
        ti = TechIndicators(key=config('ALPHA_VANTAGE'),
                            output_format='pandas')

        # Clean technical indicator abbreviations
        new_indicators = ["get_"+indicator.lower() for indicator in tech_symbols]

        # Loop to populate and merge old and new data
        i_count = 0
        for ind in new_indicators:

            data, meta_data = getattr(ti, ind)(symbol=symbol)

            # Print Statement
            print('###################################################################','\n',
            'Ticker: ' , meta_data['1: Symbol'], '\n',
            'Last Refreshed: ', meta_data['2: Indicator'], '\n',
            'Data Retrieved: ', meta_data['3: Last Refreshed'],'\n',
            '###################################################################')

            # Rename Column
            c_name = str(data.columns[0])
            data = data.rename(columns={
                c_name : symbol+'_'+c_name
            }
        )
            # Merge
            if i_count == 0:
                final_df = primary_df.merge(data,
                                            how='inner',
                                            on='date')
            else:
                final_df = final_df.merge(data,
                                        how='inner',
                                        on='date')
            i_count+=1
        return final_df

    def add_forex(self, from_currency, to_currency, primary_df):
        """
        Adds FOREX rates to the dataset. Currently only incorporates a couple of years
        ############ Recommend against using until improved ##########################

        Parameters
        ----------
        from_currency : str
            Currency being compared to another currency
        to_currency : str
            Second currency being compared to the first.
        primary_df : pandas dataframe
            pandas dataframe to be appended.

        Calculation
        -----------
        forex_value = (from_currency / to_currency)
        """
        # API Object
        cc = ForeignExchange(key=config('ALPHA_VANTAGE'),
                             output_format='pandas')

        # API Call
        data = cc.get_currency_exchange_daily(from_symbol=from_currency,
                                              to_symbol=to_currency,
                                              outputsize=self.outputsize)

        data = data.rename(columns={
            '1. open'  : from_currency+'_to_'+to_currency+'_open',
            '2. high'  : from_currency+'_to_'+to_currency+'_high',
            '3. low'   : from_currency+'_to_'+to_currency+'_low',
            '4. close' : from_currency+'_to_'+to_currency+'_close',
        }
    )
        final_df = primary_df.merge(data,
                                    how='inner',
                                    on='date')
        return final_df

    def add_treasury_bonds(self, primary_df):
        """
        Adds US treasury Bond interest rates to the dataset. Contains a wide-swath of
        available and unavailable bonds. Several features contain a large number of null
        values. Will warn about those null values in the print statement.

        Parameters
        ----------
        primary_df : pandas dataframe
            pandas dataframe to be appended.
       """
        # API Call
        data = quandl.get("USTREASURY/BILLRATES",
                        authtoken=config('QUANDL_KEY'))

        # Checking for nulls
        nulls = data.isnull().sum()

        # Print statements for status checks
        print("######### US Treasury Bond Rates Added #########")
        print('##### New columns that contain null values #####')
        print('################################################','\n')
        for i in np.arange(len(nulls)):
            if nulls[i] > 0:
                print("#####",nulls.index[i])
        print()
        print('################################################')

        data.index.name = 'date'

        # Final Merge
        final_df = primary_df.merge(data,
                                    how='inner',
                                    on='date')
        return final_df

    def add_macro(self, primary_df, indices):
        """
        Adds macroeconomic indicators from a list of indices and merges that
        data with the existing dataframe. Only accepts a list of indices.
        Parameters
        ----------
        indices : list
            list of index symbols to add to the dataframe.
        primary_df : pandas dataframe
            pandas dataframe to be appended.
        """
        warnings.warn("Some of the indices do not have recent values and performing a merge with the trading data would limit the number of observations.")

        index_dict = {
                "housing_index" : "YALE/NHPI",
                "confidence_index" : "YALE/US_CONF_INDEX_VAL_INDIV",
                "trade_index" : "FRED/TWEXB",
                "longterm_rates" : "USTREASURY/LONGTERMRATES",
                "shortterm_rates" : "USTREASURY/BILLRATES"
                }
        
        # Loop through the list of indices
        i_count = 0
        for i in indices:
            x = str(index_dict[i])
            data = quandl.get(x,
                              authtoken=self.quandl_key)
            data.index.name = 'date'
            start_date = data.index.min() - pd.DateOffset(day=1)
            end_date = data.index.max() + pd.DateOffset(day=31)
            dates = pd.date_range(start_date, end_date, freq = 'D')
            dates.name = 'date'
            data = data.reindex(dates, method = 'ffill')
            data.index = data.index.astype(str)

        # Elif statements for changing the column names

            if i == "housing_index":
                data = data.rename(columns = {'Index' : 'housing_index'})
            
                print("Housing Data Added to the Existing DataFrame")

                warnings.warn("The latest value available for Housing Index is from January 2019.")
            
            elif i == "trade_index":
                data = data.rename(columns = {'Value': 'trade_value'})
            
                print("Trade Index Added to the Existing DataFrame.")
                warnings.warn("The values for Trade Index are recorded on a weekly basis.")
            elif i == "confidence_index":
                data = data.rename(columns = {'Index Value' : 'conf_index', 'Standard Error': 'conf_index_SE'})
            
                print("Confidence Index Added to the Existing DataFrame.")
                warnings.warn("The value for confidence index are available in a monthly basis")

            elif i == "longterm_rates":
                data = data.rename(columns = {'LT Composite > 10 Yrs': '10 Yrs Rates', 'Treasury 20-Yr CMT': '20-Yr Maturity Rate'})
                data = data.drop(columns = 'Extrapolation Factor')

                print("Longterm Rates Added to the Existing DataFrame.")

            elif i == "shortterm_rates":
                data = data.rename(columns = {'4 Wk Bank Discount Rate': '4_Wk_DR',
                                            '4 Wk Coupon Equiv': '4_Wk_CE',
                                            '8 Wk Bank Discount Rate' : '8_Wk_DR',
                                            '8 Wk Coupon Equiv' : '8_Wk_CE',
                                            '13 Wk Bank Discount Rate' : '13_Wk_DR',
                                            '13 Wk Coupon Equiv': '13_Wk_CE',
                                            '26 Wk Bank Discount Rate': '26_Wk_DR',
                                            '26 Wk Coupon Equiv': '26_Wk_CE',
                                            '52 Wk Bank Discount Rate': '52_Wk_DR',
                                            '52 Wk Coupon Equiv': '52_Wk_CE'})
            
                print("Shortterm Rates Added to the Existing DataFrame.")

            else: 
                pass     

            if i_count == 0:
                final_df = primary_df.merge(data,
                                        how='inner',
                                        on='date')
            else:
                final_df = final_df.merge(data,
                                      how='inner',
                                      on='date')
            i_count+=1

            

        return final_df
