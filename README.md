# JoinQuant
本库储存用于JQ的自编函数
--------------2020/06/21-------------- 
上传Order modudule
内有自编调仓函数，JQ提供的API需要利用for loop循环执行买卖操作，缺点是不能直接对portfolio执行操作，组合内的权重及资金仓位均须另写函数实现
自编的position_adjust函数，用于直接对策略信号生成组合进行卖卖操作。可声明仓位比例、组合内权重方法(value weighted, equal weighted, etc.)
