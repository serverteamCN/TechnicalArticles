# 1	工具简介 #
在ArcGIS GeoAnalytics Server中可以将多种格式的数据注册为可供大数据分析工具使用的源数据，包括带分隔符的文本文件、Shapefile、要素服务等等。大数据分析工具对输入数据的格式有一定要求，比如必须包含唯一标识字段、必须有可识别的位置信息等，而直接从各种来源获取到的大数据未必符合GeoAnalytics Server的要求，或者包含过多的冗余信息，所以在进行大数据分析前应该对原始数据进行清理，以提高整个分析流程的效率。
本工具以批量处理*.csv文件为例，利用Python（3.x）实现了部分常用的数据清洗功能，以方便在矢量大数据分析方面的应用。
# 2	功能说明 #
工具中处理数据部分主要利用了Python中的Pandas库，以及uuid库用来添加唯一识别码。
## 2.1 	数据清洗 ##
2.1.1 	删除多余字段
通过pandas.DataFrame(data=None, index=None, columns=None, dtype=None, copy=False)[source]
筛选出需要用到的字段：

    df = pandas.read_csv(inputCSV)
    selectCols = df[['MmeUeS1apId', 'Latitude','Longitude','TimeStamp']]

2.1.2 	删除异常数据
通过查询条件过滤掉不符合要求的异常数据，如坐标值为零的数据：

    removeRows = selectCols[(selectCols.Latitude != 0) & (selectCols.Longitude != 0)]

2.1.3 	转换时间戳格式
通过pandas.to_datetime(*args, **kwargs) 转换时间戳为可识读的日期时间格式：

    removeRows['TimeStamp'] = pandas.to_datetime(removeRows['TimeStamp'], unit = 'ms')

## 2.2 	数据回填 ##
ArcGIS GeoAnalytics Server要求输入的数据必须包含唯一标识字段，如ObjectID, 对于没有OID字段的数据需要在前期数据处理时添加。如果数据没有表头字段信息，在注册至Server中时会自动添加上col_1、col_2等默认的名称，这样虽然不影响分析工具的使用，但是不易于识读每个字段代表的是什么，所以建议也在前期数据处理时回填上表头信息。
2.2.1 	添加表头字段
通过pandas.DataFrame.columns属性添加表头字段，如：

    df = pandas.read_csv(inputCSV, header=None)
    df.columns = ['MmeUeS1apId', 'Latitude','Longitude','TimeStamp','LteScRSRP','LteScRSRQ','LteScTadv']

2.2.2 	添加UUID
 通过uuid.uuid4()创建随机uuid并追加至数据中，如：

    for i, row in removeRows.iterrows():
    	removeRows.set_value(i, 'UUID',uuid.uuid4())

# 3	参数设置 #
本工具接受3个参数，第一个参数为批量输入的*.gz压缩文件路径（至文件夹层级），第二个参数为批量输出的*.csv文件路径（至文件夹层级），第三个参数为原始数据是否包含表头信息（“T”或“F”）。
如：E:\>python DataCleaning.py e:\OriginData e:\Result T
另外在脚本内部有一些设置需要根据输入的数据进行调整，如添加的表头字段内容列表（df.columns）、需要保留的字段列表（selectCols）、剔除异常字段的查询语句（selectCols.Latitude != 0）、时间戳格式等。
# 4	使用示例 #
## 4.1 	组织原始数据 ##
将所有待处理的*.gz文件放在E:\OriginData目录下：
 
![](http://i.imgur.com/4agHIs0.png)
![](http://i.imgur.com/7A8llmt.png)
 
## 4.2 	运行脚本工具 ##
将本工具的脚本DataCleaning.py放在E:\根目录下，在command窗口中执行：
E:\>python DataCleaning.py e:\OriginData e:\Result T

![](http://i.imgur.com/RCp5aTY.png)
 
## 4.3 	查看执行结果 ##
处理后的*.csv数据将被输出至E:\Result路径下：

![](http://i.imgur.com/XlAx03Z.png)
![](http://i.imgur.com/5eHTcYf.png)
 
# 5. 下载链接 #
https://github.com/oopsliu/Data-Cleaning-Tool
