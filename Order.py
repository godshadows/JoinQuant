from kuanke.user_space_api import *
import pandas as pd
import numpy as np


def position_adjust(portfolio_list, percentage, method, context):
    '''调仓函数'''
    position_dict = context.portfolio.positions
    current_data = get_current_data()
    stock_in_account = list(position_dict.keys())
    stock_amount_df = pd.DataFrame(0,
                                   index=set(stock_in_account +
                                             portfolio_list),
                                   columns=['account_amount'])
    stock_amount_df.account_amount.update(
        pd.Series([
            position_dict[security].total_amount
            for security in stock_in_account
        ],
                  index=stock_in_account))
    stock_amount_df['target_amount'] = pd.Series(
        0,
        index=[
            security for security in stock_in_account
            if security not in portfolio_list
        ])
    if len(stock_in_account) != 0:
        stock_amount_df[['target_amount'
                         ]][stock_amount_df.target_amount == 0].apply(
                             lambda x: order_target(x.name, 0), axis=1)
    # 将account中不在新组合中的stock先卖出，方便后续计算权重时提供更精确的total_avai_value
    if len(portfolio_list) != 0:
        if len(portfolio_list)==1:
            order_value(portfolio_list[0], context.portfolio.available_cash)
        else:
            stock_amount_df.target_amount = pd.Series(weight_fun_dict[method](
                portfolio_list, percentage, context),
                                                      index=portfolio_list)
            # 直接赋值，早先卖出的非组合账户内股票部分成nan，不影响后续diff<0的判断
            if not all(pd.isna(stock_amount_df.target_amount)):  # 判断组合权重是否构建成功
                stock_amount_df[
                    'diff'] = stock_amount_df.target_amount - stock_amount_df.account_amount
                stock_amount_df['diff']=stock_amount_df['diff'].apply(lambda x: 0 if np.abs(x) < 100 else x)
                stock_amount_df[['target_amount'
                                 ]][stock_amount_df['diff'] < 0].apply(
                                     lambda x: order_target(x.name, x.iloc[0]),
                                     axis=1)
                stock_amount_df[['target_amount'
                                 ]][stock_amount_df['diff'] > 0].apply(
                                     lambda x: order_target(x.name, x.iloc[0]),
                                     axis=1)


def equal_amount(portfolio_list, percentage, context):
    '''equal amount先将账户中组合以外的股票卖出再计算组合weight，仓位更精确'''
    position_dict = context.portfolio.subportfolios[0].long_positions
    current_data = get_current_data()
    #-----------------------计算账户有效资产总价值（现金+股票）-----------------------
    cash_avai_value = context.portfolio.subportfolios[0].available_cash
    account_stock_value = context.portfolio.subportfolios[0].positions_value
    account_paused_stock_total_value = sum([
        position_dict[stock].value for stock in position_dict.keys()
        if current_data[stock].paused
    ])  # 排除停牌不可卖的股票价值
    total_avai_value = cash_avai_value + account_stock_value - account_paused_stock_total_value
    #---------------------------------------------------------------------------------

    weight_list = np.ones(len(portfolio_list))
    # equal amount
    price_portfolio_available_list = np.array(
        [current_data[code].last_price for code in portfolio_list])
    portfolio_share = np.floor(total_avai_value * percentage /
                               price_portfolio_available_list.sum())
    if portfolio_share == 0:
        log.info('构建组合不足1份，换仓失败')
        return []
    else:
        portfolio_amount_list = portfolio_share * weight_list
        return portfolio_amount_list

def equal_weighted(portfolio_list, percentage, context):
    '''equal amount先将账户中组合以外的股票卖出再计算组合weight，仓位更精确'''
    position_dict = context.portfolio.subportfolios[0].long_positions
    current_data = get_current_data()
    #-----------------------计算账户有效资产总价值（现金+股票）-----------------------
    cash_avai_value = context.portfolio.subportfolios[0].available_cash
    account_stock_value = context.portfolio.subportfolios[0].positions_value
    account_paused_stock_total_value = sum([
        position_dict[stock].value for stock in position_dict.keys()
        if current_data[stock].paused
    ])  # 排除停牌不可卖的股票价值
    total_avai_value = cash_avai_value + account_stock_value - account_paused_stock_total_value
    #---------------------------------------------------------------------------------

    value_list = np.ones(
        len(portfolio_list)) * total_avai_value / len(portfolio_list)
    # equal values
    price_portfolio_available_list = np.array(
        [current_data[code].last_price for code in portfolio_list])

    portfolio_amount_list = value_list / price_portfolio_available_list
    return portfolio_amount_list

def value_weighted(portfolio_list, percentage, context):
    '''equal amount先将账户中组合以外的股票卖出再计算组合weight，仓位更精确'''
    from jqdata import get_valuation
    from dateutil.relativedelta import relativedelta
    #mkt_cap_df = get_valuation(portfolio_list, end_date=context.current_dt-relativedelta(days=1), count=1, fields=['circulating_market_cap'])
    #有bug，若当日上市，则无上一日市值，数据库返回df直接少一行，而不是给nan
    mkt_cap_df = get_valuation(portfolio_list, end_date=context.current_dt, count=1, fields=['circulating_market_cap'])
    value_weighted_list = mkt_cap_df['circulating_market_cap'].values/mkt_cap_df['circulating_market_cap'].sum()
    position_dict = context.portfolio.subportfolios[0].long_positions
    current_data = get_current_data()
    #-----------------------计算账户有效资产总价值（现金+股票）-----------------------
    cash_avai_value = context.portfolio.subportfolios[0].available_cash
    account_stock_value = context.portfolio.subportfolios[0].positions_value
    account_paused_stock_total_value = sum([
        position_dict[stock].value for stock in position_dict.keys()
        if current_data[stock].paused
    ])  # 排除停牌不可卖的股票价值
    total_avai_value = cash_avai_value + account_stock_value - account_paused_stock_total_value
    #---------------------------------------------------------------------------------

    value_list = total_avai_value * value_weighted_list
    # values weighted
    price_portfolio_available_list = np.array(
        [current_data[code].last_price for code in portfolio_list])

    portfolio_amount_list = value_list / price_portfolio_available_list
    return portfolio_amount_list
weight_fun_dict = {
    'equal_amount': equal_amount,
    'value_weighted': value_weighted,
    'price_weighted': 0,
    'equal_weighted': equal_weighted,
}
